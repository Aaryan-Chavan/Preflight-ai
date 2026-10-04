const functions = require("firebase-functions");
const admin = require("firebase-admin");

admin.initializeApp();
const db = admin.firestore();

exports.syncReport = functions.https.onRequest(async (req, res) => {
    // 1. Enforce POST requests only
    if (req.method !== "POST") {
        return res.status(405).send("Method Not Allowed");
    }

    // 2. Extract the Authorization Header
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith("Bearer ")) {
        return res.status(401).send("Unauthorized: Missing Bearer Token");
    }
    
    const idToken = authHeader.split("Bearer ")[1];

    try {
        // 3. Verify the token with Firebase Auth
        const decodedToken = await admin.auth().verifyIdToken(idToken);
        const uid = decodedToken.uid;
        
        // 4. Parse the report data from Python
        const reportData = req.body;
        
        if (!reportData.report_id) {
            return res.status(400).send("Bad Request: Missing report_id");
        }

        // 5. Append server-side metadata for security
        const payloadToSave = {
            ...reportData,
            userId: uid, // Strictly binds this report to the authenticated user
            cloudSyncedAt: admin.firestore.FieldValue.serverTimestamp()
        };

        // 6. Write to Firestore
        await db.collection("reports").doc(reportData.report_id).set(payloadToSave);

        console.log(`✅ Successfully synced report ${reportData.report_id} for user ${uid}`);
        return res.status(200).json({ success: true, message: "Report synced successfully" });
        
    } catch (error) {
        console.error("Token verification or DB write failed:", error);
        return res.status(403).send("Forbidden: Invalid Token or Server Error");
    }
});