// 1. Set up your Security Badge and URL
const API_KEY = "MALIBORA_SECRET_KEY_2026";
const API_URL = window.location.origin; // Automatically uses your live Render link

// 2. The function to Read from the Cloud Database
async function loadTrucksFromCloud() {
    try {
        // Knock on the FastAPI door and show the badge
        const response = await fetch(`${API_URL}/api/trucks`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                "X-API-Key": API_KEY 
            }
        });

        // Convert the response into a list of trucks
        const trucks = await response.json();
        
        // Clear your current list on the screen
        const truckListElement = document.getElementById("truck-list"); // Make sure this matches your HTML ID
        truckListElement.innerHTML = ""; 

        // Loop through the database records and put them on the screen
        trucks.forEach(truck => {
            const li = document.createElement("li");
            li.textContent = `Plate: ${truck.plate} | Model: ${truck.model}`;
            truckListElement.appendChild(li);
        });

        console.log("Successfully loaded trucks from Supabase!");

    } catch (error) {
        console.error("Database connection failed:", error);
    }
}

// 3. Make sure it runs as soon as the page loads!
window.onload = () => {
    loadTrucksFromCloud();
};