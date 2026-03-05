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
};// 4. The function to Send a NEW truck to the Cloud Database
const truckForm = document.getElementById("truck-form"); // Change if your form has a different ID

if (truckForm) {
    truckForm.addEventListener("submit", async (event) => {
        event.preventDefault(); // This stops the page from doing a hard reload

        // Grab the text you typed into the boxes
        const newPlate = document.getElementById("truck-plate").value; // Change if your input ID is different
        const newModel = document.getElementById("truck-model").value; // Change if your input ID is different

        try {
            // Shoot the data to the FastAPI server
            const response = await fetch(`${API_URL}/api/trucks`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-API-Key": API_KEY 
                },
                // Package the data exactly how Python expects it
                body: JSON.stringify({ plate: newPlate, model: newModel })
            });

            if (response.ok) {
                console.log("New truck safely locked in the cloud!");
                
                // Clear the text boxes so they are empty for the next truck
                document.getElementById("truck-plate").value = "";
                document.getElementById("truck-model").value = "";
                
                // Magically refresh the list on the screen so the new truck appears instantly!
                loadTrucksFromCloud();
            } else {
                console.error("The server rejected the truck.");
            }
        } catch (error) {
            console.error("Failed to connect to the cloud:", error);
        }
    });
}