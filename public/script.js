// ==========================================
// THE CLOUD SYNCHRONIZER (B2B SaaS Engine)
// ==========================================
// This script runs in the background and silently syncs the cloud data
// with the beautiful local dashboard UI.

// These variables are already defined in index.html, but we reference them here
// const API_KEY = 'MALIBORA_SECRET_KEY_2026';
// const API_URL = window.location.origin;
// let currentCompanyId = null; 
// let db = { ... }
// function renderAll() { ... }

/**
 * MASTER CLOUD SYNC FUNCTION
 * This is called automatically from index.html right after a successful login.
 */
async function syncDashboardWithCloud() {
    if (!currentCompanyId) {
        console.error("Cannot sync: No company logged in.");
        return;
    }

    try {
        console.log(`Starting Cloud Sync for Company ID: ${currentCompanyId}...`);

        // 1. Fetch all data in parallel for maximum speed
        const [trucksRes, driversRes, expensesRes, inventoryRes] = await Promise.all([
            fetch(`${API_URL}/api/trucks?company_id=${currentCompanyId}`, { headers: { "X-API-Key": API_KEY } }),
            fetch(`${API_URL}/api/drivers?company_id=${currentCompanyId}`, { headers: { "X-API-Key": API_KEY } }),
            fetch(`${API_URL}/api/expenses?company_id=${currentCompanyId}`, { headers: { "X-API-Key": API_KEY } }),
            fetch(`${API_URL}/api/inventory?company_id=${currentCompanyId}`, { headers: { "X-API-Key": API_KEY } })
        ]);

        // 2. Unpack the JSON data
        const cloudTrucks = await trucksRes.json();
        const cloudDrivers = await driversRes.json();
        const cloudExpenses = await expensesRes.json();
        const cloudInventory = await inventoryRes.json();

        // 3. Translate Cloud Data into Dashboard Format
        
        // A. Format Trucks
        db.trucks = cloudTrucks.map(t => ({
            id: t.id,
            plate: t.plate,
            model: t.model,
            trailers: 0, // Defaulting for now
            interval: 5000, 
            odo: 0, 
            lastServiceOdo: 0
        }));

        // B. Format Drivers
        db.drivers = cloudDrivers.map(d => ({
            id: d.id,
            name: d.name,
            customer: "", 
            truck: "" 
        }));

        // C. Format Inventory
        db.inventory = cloudInventory.map(i => ({
            id: i.id,
            type: i.item_type,
            serial: i.serial_number,
            truck: i.assigned_truck,
            cost: i.cost
        }));

        // D. Format Expenses (Adding them to the transaction history)
        // We will filter out old pure-cloud expenses to prevent duplicates, then inject fresh ones
        db.txs = db.txs.filter(tx => tx.type !== 'expense' || !tx.isCloudSync); 
        
        const expenseTxs = cloudExpenses.map(e => {
            // Try to split the Python description back into Category and Desc
            let cat = "Other";
            let desc = e.description;
            if(e.description && e.description.includes(" - ")) {
                let parts = e.description.split(" - ");
                cat = parts[0];
                desc = parts.slice(1).join(" - ");
            }

            return {
                id: e.id,
                date: new Date().toISOString().slice(0, 10), // Default to today since we didn't store date in phase 1
                truck: "N/A", // Defaulting for simple expenses
                driver: "System",
                desc: desc,
                cat: cat,
                amount: e.amount,
                type: 'expense',
                isCloudSync: true // Marker so we know it came from Supabase
            };
        });

        // Merge cloud expenses into the dashboard history
        db.txs = [...db.txs, ...expenseTxs];

        // 4. Save to local memory buffer and draw the UI!
        saveLocal(); // Assuming this is defined in index.html
        renderAll(); // Refresh the beautiful dashboard!
        
        console.log("Cloud Sync Complete! Dashboard is live.");

    } catch (error) {
        console.error("Critical Cloud Sync Failure:", error);
        alert("Warning: Could not pull live data from the cloud. Please check your connection.");
    }
}
