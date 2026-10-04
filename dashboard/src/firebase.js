import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyB4eLLKNu0u-GUigSNMEX0Wwicyg0Aowys",
  authDomain: "preflight-aaryan1910.firebaseapp.com",
  projectId: "preflight-aaryan1910",
  storageBucket: "preflight-aaryan1910.firebasestorage.app",
  messagingSenderId: "679252678316",
  appId: "1:679252678316:web:a999a582dc5bf09c15b109"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Export instances to use in your React components
export const db = getFirestore(app);
export const auth = getAuth(app);
export const provider = new GoogleAuthProvider();