const axios = require('axios');

async function test() {
    try {
        const response = await axios.get('http://127.0.0.1:8000/api/v1/grievances/');
        console.log("Status:", response.status);
        console.log("Data type:", typeof response.data);
        console.log("Data snippet:", String(response.data).substring(0, 100));
    } catch (err) {
        console.error("Error:", err.message);
    }
}
test();
