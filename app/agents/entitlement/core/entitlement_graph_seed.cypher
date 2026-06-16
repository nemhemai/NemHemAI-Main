CREATE CONSTRAINT scheme_name_unique IF NOT EXISTS
FOR (s:Scheme) REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT criterion_id_unique IF NOT EXISTS
FOR (c:EligibilityCriterion) REQUIRE c.criterion_id IS UNIQUE;

CREATE CONSTRAINT exclusion_id_unique IF NOT EXISTS
FOR (e:ExclusionRule) REQUIRE e.rule_id IS UNIQUE;

MERGE (pmayu:Scheme {name: "PMAY-U"})
SET pmayu.category = "housing",
    pmayu.benefit = "Urban housing assistance under PMAY-U 2.0";

MERGE (pmayg:Scheme {name: "PM Awas Yojana"})
SET pmayg.category = "housing",
    pmayg.benefit = "Rural housing assistance under PMAY-G/PM Awas Yojana";

MERGE (svanidhi:Scheme {name: "PM SVANidhi"})
SET svanidhi.category = "urban_livelihood",
    svanidhi.benefit = "Working capital loan support for eligible street vendors";

MERGE (kusum:Scheme {name: "PM-KUSUM"})
SET kusum.category = "agriculture_energy",
    kusum.benefit = "Solar pump and grid-connected solarization support for farmers";

MERGE (scholarship:Scheme {name: "Post-Matric Scholarship"})
SET scholarship.category = "education",
    scholarship.benefit = "Post-matric education scholarship support";

MERGE (pmkisan:Scheme {name: "PM-KISAN"})
SET pmkisan.category = "agriculture_income_support",
    pmkisan.benefit = "Income support for eligible landholding farmer families";

WITH 1 AS _
UNWIND [
  ["PMAY-U", "pmayu_area", "Applicant is in an urban area", "urban_rural", "equals", "urban"],
  ["PMAY-U", "pmayu_no_pucca", "Household does not own a pucca house", "has_pucca_house", "is_false", null],
  ["PMAY-U", "pmayu_income", "Annual income is within PMAY-U income bands", "income_annual", "lte", 1800000],
  ["PM Awas Yojana", "pmayg_area", "Applicant is in a rural area", "urban_rural", "equals", "rural"],
  ["PM Awas Yojana", "pmayg_no_pucca", "Household does not own a pucca house", "has_pucca_house", "is_false", null],
  ["PM SVANidhi", "svanidhi_vendor", "Applicant is a street vendor", "occupation", "equals", "street_vendor"],
  ["PM SVANidhi", "svanidhi_authorization", "Vending certificate or ULB/TVC recommendation is available", "has_vending_certificate", "or_true", "has_ulb_recommendation"],
  ["PM-KUSUM", "kusum_farmer", "Applicant is a farmer", "occupation", "equals", "farmer"],
  ["PM-KUSUM", "kusum_land", "Applicant has cultivable land for solar pump/plant use", "land_ownership_acres", "positive_number", null],
  ["Post-Matric Scholarship", "pms_education", "Applicant is enrolled in a post-matric course", "education_level", "equals", "post_matric"],
  ["Post-Matric Scholarship", "pms_category", "Applicant belongs to SC, ST, or OBC category", "category", "in", "SC,ST,OBC"],
  ["Post-Matric Scholarship", "pms_income", "Parental/household income is within category threshold", "income_annual", "category_income_threshold", "SC/ST:250000,OBC:100000"],
  ["PM-KISAN", "pmkisan_farmer", "Applicant is a farmer", "occupation", "equals", "farmer"],
  ["PM-KISAN", "pmkisan_land", "Applicant has cultivable land ownership", "land_ownership_acres", "positive_number", null],
  ["PM-KISAN", "pmkisan_aadhaar", "Aadhaar is available/seeded", "has_aadhaar", "is_true", null],
  ["PM-KISAN", "pmkisan_bank", "Bank account is available", "has_bank_account", "is_true", null]
] AS row
MATCH (s:Scheme {name: row[0]})
MERGE (c:EligibilityCriterion {criterion_id: row[1]})
SET c.label = row[2],
    c.attribute = row[3],
    c.operator = row[4],
    c.expected_value = row[5]
MERGE (s)-[:HAS_CRITERION]->(c);

WITH 1 AS _
UNWIND [
  ["PM Awas Yojana", "pmayg_govt_employee", "Government employee exclusion", "is_govt_employee", "is_true"],
  ["PM Awas Yojana", "pmayg_income_tax", "Income tax payer exclusion", "pays_income_tax", "is_true"],
  ["PM Awas Yojana", "pmayg_vehicle", "Motorized vehicle ownership exclusion", "owns_motorized_vehicle", "is_true"],
  ["PM-KISAN", "pmkisan_institutional", "Institutional landholder exclusion", "is_institutional_landholder", "is_true"],
  ["PM-KISAN", "pmkisan_govt_employee", "Government employee exclusion", "is_govt_employee", "is_true"],
  ["PM-KISAN", "pmkisan_income_tax", "Income tax payer exclusion", "pays_income_tax", "is_true"]
] AS row
MATCH (s:Scheme {name: row[0]})
MERGE (e:ExclusionRule {rule_id: row[1]})
SET e.label = row[2],
    e.attribute = row[3],
    e.operator = row[4]
MERGE (s)-[:EXCLUDES]->(e);
