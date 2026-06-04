# app/utils/element_id_utils.py

def generate_element_id(document_id, page_number, sequence_order):

    if page_number is None:
        page_number = 0

    return f"{document_id}_p{page_number}_e{sequence_order}"