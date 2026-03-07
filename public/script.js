const API_KEY = "MALIBORA_SECRET_KEY_2026";
const API_URL = window.location.origin;

// This is the master memory variable. It stays empty until someone logs in!
let currentCompanyId = null; 

// ==========================================
// 0. B2B LOGIN SYSTEM
// ==========================================
const loginBtn = document.getElementById("login-btn");
if (loginBtn) {
    loginBtn.addEventListener("click", async () => {
        const companyName = document.getElementById("company-name").value;
        if (!companyName) {
            alert("Please enter a company name!");
            return;
        }

        try {
            const response = await fetch(`${API_URL}/api/companies`, {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
                body: JSON.stringify({ company_name: companyName })
            });

            const data = await response.json();
            
            if (response.ok) {
                // Save the company ID into the app's memory
                currentCompanyId = data.company_id;
                document.getElementById("login-message").textContent = data.message;
                
                // Wait 1 second, then hide the login screen and show the main dashboard
                setTimeout(() => {
                    document.getElementById("login-screen").style.display = "none";
                    document.getElementById("main-app").style.display = "block";
                    
                    // NOW load the data specifically for this company!
                    loadTrucksFromCloud();
                    loadDriversFromCloud();
                    loadExpensesFromCloud();
                    loadInventoryFromCloud();
                }, 1000);
            }
        } catch (error) {
            console.error("Login failed:", error);
        }
    });
}

// ==========================================
// 1. TRUCKS CABIN
// ==========================================
async function loadTrucksFromCloud() {
    try {
        const response = await fetch(`${API_URL}/api/trucks?company_id=${currentCompanyId}`, { method: "GET", headers: { "X-API-Key": API_KEY } });
        const trucks = await response.json();
        const truckListElement = document.getElementById("truck-list");
        if (truckListElement) {
            truckListElement.innerHTML = ""; 
            trucks.forEach(truck => {
                const li = document.createElement("li");
                li.textContent = `Plate: ${truck.plate} | Model: ${truck.model}`;
                truckListElement.appendChild(li);
            });
        }
    } catch (error) { console.error("Database connection failed:", error); }
}

const truckForm = document.getElementById("truck-form");
if (truckForm) {
    truckForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const newPlate = document.getElementById("truck-plate").value;
        const newModel = document.getElementById("truck-model").value;

        try {
            const response = await fetch(`${API_URL}/api/trucks`, {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
                body: JSON.stringify({ plate: newPlate, model: newModel, company_id: currentCompanyId })
            });
            if (response.ok) {
                document.getElementById("truck-plate").value = "";
                document.getElementById("truck-model").value = "";
                loadTrucksFromCloud();
            }
        } catch (error) { console.error("Failed to connect:", error); }
    });
}

// ==========================================
// 2. DRIVERS CABIN
// ==========================================
async function loadDriversFromCloud() {
    try {
        const response = await fetch(`${API_URL}/api/drivers?company_id=${currentCompanyId}`, { method: "GET", headers: { "X-API-Key": API_KEY } });
        const data = await response.json();
        const listElement = document.getElementById("driver-list");
        if (listElement) {
            listElement.innerHTML = "";
            data.forEach(d => {
                const li = document.createElement("li");
                li.textContent = `Name: ${d.name}`;
                listElement.appendChild(li);
            });
        }
    } catch (error) { console.error("Database connection failed:", error); }
}

const driverForm = document.getElementById("driver-form");
if (driverForm) {
    driverForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const newName = document.getElementById("driver-name").value;
        try {
            const response = await fetch(`${API_URL}/api/drivers`, {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
                body: JSON.stringify({ name: newName, company_id: currentCompanyId })
            });
            if (response.ok) {
                document.getElementById("driver-name").value = "";
                loadDriversFromCloud();
            }
        } catch (error) { console.error("Failed to connect:", error); }
    });
}

// ==========================================
// 3. EXPENSES CABIN
// ==========================================
async function loadExpensesFromCloud() {
    try {
        const response = await fetch(`${API_URL}/api/expenses?company_id=${currentCompanyId}`, { method: "GET", headers: { "X-API-Key": API_KEY } });
        const data = await response.json();
        const listElement = document.getElementById("expense-list");
        if (listElement) {
            listElement.innerHTML = "";
            data.forEach(e => {
                const li = document.createElement("li");
                li.textContent = `Desc: ${e.description} | Amount: ${e.amount} | Fine: ${e.is_fine}`;
                listElement.appendChild(li);
            });
        }
    } catch (error) { console.error("Database connection failed:", error); }
}

const expenseForm = document.getElementById("expense-form");
if (expenseForm) {
    expenseForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const newDesc = document.getElementById("expense-desc").value;
        const newAmount = parseInt(document.getElementById("expense-amount").value);
        const newIsFine = document.getElementById("expense-fine") ? document.getElementById("expense-fine").checked : false;
        
        try {
            const response = await fetch(`${API_URL}/api/expenses`, {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
                body: JSON.stringify({ description: newDesc, amount: newAmount, is_fine: newIsFine, company_id: currentCompanyId })
            });
            if (response.ok) {
                document.getElementById("expense-desc").value = "";
                document.getElementById("expense-amount").value = "";
                loadExpensesFromCloud();
            }
        } catch (error) { console.error("Failed to connect:", error); }
    });
}

// ==========================================
// 4. INVENTORY CABIN
// ==========================================
async function loadInventoryFromCloud() {
    try {
        const response = await fetch(`${API_URL}/api/inventory?company_id=${currentCompanyId}`, { method: "GET", headers: { "X-API-Key": API_KEY } });
        const data = await response.json();
        const listElement = document.getElementById("inventory-list");
        if (listElement) {
            listElement.innerHTML = "";
            data.forEach(i => {
                const li = document.createElement("li");
                li.textContent = `Item: ${i.item_type} | SN: ${i.serial_number} | Truck: ${i.assigned_truck} | Cost: ${i.cost}`;
                listElement.appendChild(li);
            });
        }
    } catch (error) { console.error("Database connection failed:", error); }
}

const inventoryForm = document.getElementById("inventory-form");
if (inventoryForm) {
    inventoryForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const newType = document.getElementById("inventory-type").value;
        const newSerial = document.getElementById("inventory-serial").value;
        const newTruck = document.getElementById("inventory-truck").value;
        const newCost = parseInt(document.getElementById("inventory-cost").value);
        
        try {
            const response = await fetch(`${API_URL}/api/inventory`, {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
                body: JSON.stringify({ item_type: newType, serial_number: newSerial, assigned_truck: newTruck, cost: newCost, company_id: currentCompanyId })
            });
            if (response.ok) {
                document.getElementById("inventory-type").value = "";
                document.getElementById("inventory-serial").value = "";
                document.getElementById("inventory-truck").value = "";
                document.getElementById("inventory-cost").value = "";
                loadInventoryFromCloud();
            }
        } catch (error) { console.error("Failed to connect:", error); }
    });
}
// 3. Make sure it runs as soon as the page loads!
// 3. Make sure ALL data loads as soon as the page opens!
window.onload = () => {
    loadTrucksFromCloud();
    loadDriversFromCloud();
    loadExpensesFromCloud();
    loadInventoryFromCloud();
};
// 4. The function to Send a NEW truck to the Cloud Database
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
// ==========================================
// 1. DRIVERS CABIN
// ==========================================
async function loadDriversFromCloud() {
    try {
        const response = await fetch(`${API_URL}/api/drivers`, { method: "GET", headers: { "X-API-Key": API_KEY } });
        const data = await response.json();
        const listElement = document.getElementById("driver-list");
        if (listElement) {
            listElement.innerHTML = "";
            data.forEach(d => {
                const li = document.createElement("li");
                li.textContent = `Name: ${d.name}`;
                listElement.appendChild(li);
            });
        }
    } catch (error) { console.error("Database connection failed:", error); }
}

const driverForm = document.getElementById("driver-form");
if (driverForm) {
    driverForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const newName = document.getElementById("driver-name").value;
        try {
            const response = await fetch(`${API_URL}/api/drivers`, {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
                body: JSON.stringify({ name: newName })
            });
            if (response.ok) {
                document.getElementById("driver-name").value = "";
                loadDriversFromCloud();
            }
        } catch (error) { console.error("Failed to connect to the cloud:", error); }
    });
}

// ==========================================
// 2. EXPENSES CABIN
// ==========================================
async function loadExpensesFromCloud() {
    try {
        const response = await fetch(`${API_URL}/api/expenses`, { method: "GET", headers: { "X-API-Key": API_KEY } });
        const data = await response.json();
        const listElement = document.getElementById("expense-list");
        if (listElement) {
            listElement.innerHTML = "";
            data.forEach(e => {
                const li = document.createElement("li");
                li.textContent = `Desc: ${e.description} | Amount: ${e.amount} | Fine: ${e.is_fine}`;
                listElement.appendChild(li);
            });
        }
    } catch (error) { console.error("Database connection failed:", error); }
}

const expenseForm = document.getElementById("expense-form");
if (expenseForm) {
    expenseForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const newDesc = document.getElementById("expense-desc").value;
        const newAmount = parseInt(document.getElementById("expense-amount").value);
        const newIsFine = document.getElementById("expense-fine") ? document.getElementById("expense-fine").checked : false;
        
        try {
            const response = await fetch(`${API_URL}/api/expenses`, {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
                body: JSON.stringify({ description: newDesc, amount: newAmount, is_fine: newIsFine })
            });
            if (response.ok) {
                document.getElementById("expense-desc").value = "";
                document.getElementById("expense-amount").value = "";
                loadExpensesFromCloud();
            }
        } catch (error) { console.error("Failed to connect to the cloud:", error); }
    });
}

// ==========================================
// 3. INVENTORY CABIN
// ==========================================
async function loadInventoryFromCloud() {
    try {
        const response = await fetch(`${API_URL}/api/inventory`, { method: "GET", headers: { "X-API-Key": API_KEY } });
        const data = await response.json();
        const listElement = document.getElementById("inventory-list");
        if (listElement) {
            listElement.innerHTML = "";
            data.forEach(i => {
                const li = document.createElement("li");
                li.textContent = `Item: ${i.item_type} | SN: ${i.serial_number} | Truck: ${i.assigned_truck} | Cost: ${i.cost}`;
                listElement.appendChild(li);
            });
        }
    } catch (error) { console.error("Database connection failed:", error); }
}

const inventoryForm = document.getElementById("inventory-form");
if (inventoryForm) {
    inventoryForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const newType = document.getElementById("inventory-type").value;
        const newSerial = document.getElementById("inventory-serial").value;
        const newTruck = document.getElementById("inventory-truck").value;
        const newCost = parseInt(document.getElementById("inventory-cost").value);
        
        try {
            const response = await fetch(`${API_URL}/api/inventory`, {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
                body: JSON.stringify({ item_type: newType, serial_number: newSerial, assigned_truck: newTruck, cost: newCost })
            });
            if (response.ok) {
                document.getElementById("inventory-type").value = "";
                document.getElementById("inventory-serial").value = "";
                document.getElementById("inventory-truck").value = "";
                document.getElementById("inventory-cost").value = "";
                loadInventoryFromCloud();
            }
        } catch (error) { console.error("Failed to connect to the cloud:", error); }
    });
}
