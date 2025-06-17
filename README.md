git init

npm install

package.json

npm run deploy

import React, { useState, useEffect } from 'react';
import { initializeApp } from 'firebase/app';
import { getAuth, signInAnonymously, signInWithCustomToken, onAuthStateChanged } from 'firebase/auth';
import { getFirestore, collection, query, onSnapshot, addDoc } from 'firebase/firestore';

// Custom Modal Component
const Modal = ({ title, message, onClose }) => {
    return (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg shadow-xl p-6 max-w-sm w-full animate-fade-in-up">
                <h3 className="text-xl font-bold text-gray-800 mb-4">{title}</h3>
                <p className="text-gray-700 mb-6">{message}</p>
                <button
                    onClick={onClose}
                    className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded-lg shadow-md transition duration-300 ease-in-out transform hover:scale-105"
                >
                    Close
                </button>
            </div>
        </div>
    );
};

// Main App component
const App = () => {
    // State variables for Firebase and user authentication
    const [db, setDb] = useState(null);
    const [auth, setAuth] = useState(null);
    const [userId, setUserId] = useState(null);
    const [isAuthReady, setIsAuthReady] = useState(false);

    // State for application flow
    const [userTaskChoice, setUserTaskChoice] = useState('');
    const [datasetFile, setDatasetFile] = useState(null);
    const [uploadedDataContent, setUploadedDataContent] = useState(''); // Stores content for AI analysis
    const [datasetHeaders, setDatasetHeaders] = useState([]); // Stores extracted headers (potential CDEs) from uploaded data
    const [dqDimensions, setDqDimensions] = useState([]);
    const [rules, setRules] = useState({});
    const [savedRules, setSavedRules] = useState([]); // To store rules fetched from Firestore
    const [currentDatasetId, setCurrentDatasetId] = useState(null); // To store dataset ID

    // State for AI analysis and recommendations
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [recommendations, setRecommendations] = useState([]);
    const [selectedRecommendations, setSelectedRecommendations] = useState([]); // To track selected AI recommendations
    const [dataElementDefinitions, setDataElementDefinitions] = useState([]); // Stores AI-generated field definitions (CDEs)
    const [isDefiningFields, setIsDefiningFields] = useState(false);

    // State for simulated DQ results and issues
    const [simulatedDQResults, setSimulatedDQResults] = useState({
        overallQualityScore: 0, // Updated to be 'overall'
        cdeQualityScores: [], // New state to hold per-CDE scores
        testedRecords: 0,
        passedRecords: 0,
        failedRecords: [],
        rulesRunCount: 0
    });
    const [unresolvedIssues, setUnresolvedIssues] = useState([]);

    // State for Regulatory Compliance
    const [regulatoryPolicyText, setRegulatoryPolicyText] = useState('');
    const [isEvaluatingCompliance, setIsEvaluatingCompliance] = useState(false);
    const [complianceReport, setComplianceReport] = useState(null); // Stores the AI-generated compliance report
    const [isProcessingFile, setIsProcessingFile] = useState(false); // New state for file processing loader

    const [showModal, setShowModal] = useState(false);
    const [modalMessage, setModalMessage] = useState('');
    const [modalTitle, setModalTitle] = useState('');

    // Function to show custom modal
    const displayModal = (title, message) => {
        setModalTitle(title);
        setModalMessage(message);
        setShowModal(true);
    };

    // Firestore setup and authentication
    useEffect(() => {
        const firebaseConfig = typeof __firebase_config !== 'undefined' ? JSON.parse(__firebase_config) : {};
        const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-app-id';

        const app = initializeApp(firebaseConfig);
        const firestoreDb = getFirestore(app);
        const firebaseAuth = getAuth(app);

        setDb(firestoreDb);
        setAuth(firebaseAuth);

        const signIn = async () => {
            try {
                if (typeof __initial_auth_token !== 'undefined') {
                    await signInWithCustomToken(firebaseAuth, __initial_auth_token);
                } else {
                    await signInAnonymously(firebaseAuth);
                }
            } catch (error) {
                console.error("Firebase authentication error:", error);
                displayModal("Authentication Error", "Failed to authenticate with Firebase. Please try again.");
            }
        };
        signIn();

        const unsubscribe = onAuthStateChanged(firebaseAuth, (user) => {
            if (user) {
                setUserId(user.uid);
            } else {
                setUserId(null);
            }
            setIsAuthReady(true);
        });

        return () => unsubscribe();
    }, []);

    // Effect to fetch saved rules from Firestore
    useEffect(() => {
        if (isAuthReady && db && userId) {
            const rulesCollectionRef = collection(db, `artifacts/${__app_id}/users/${userId}/data_quality_rules`);
            const q = query(rulesCollectionRef);

            const unsubscribe = onSnapshot(q, (snapshot) => {
                const fetchedRules = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
                setSavedRules(fetchedRules);
            }, (error) => {
                console.error("Error fetching rules from Firestore:", error);
                displayModal("Firestore Error", "Failed to fetch saved rules from the database.");
            });

            return () => unsubscribe();
        }
    }, [isAuthReady, db, userId]);

    // Handle button clicks for main menu
    const handleMainMenuClick = (choice) => {
        setUserTaskChoice(choice);
        // Reset state when navigating to a new task (unless it's applying recommendations)
        if (choice !== 'Define Data Quality Rules' || selectedRecommendations.length === 0) {
            // Do not clear uploadedDataContent, datasetFile, datasetHeaders, currentDatasetId
            // as these should persist across activities for the autonomous flow.
            setDqDimensions([]);
            setRules({});
            setRecommendations([]);
            setSelectedRecommendations([]);
            // Do not clear dataElementDefinitions either, as it's part of the persistent data analysis
            setSimulatedDQResults({
                overallQualityScore: 0,
                cdeQualityScores: [],
                testedRecords: 0,
                passedRecords: 0,
                failedRecords: [],
                rulesRunCount: 0
            });
            setUnresolvedIssues([]);
            setRegulatoryPolicyText(''); // Clear policy text when starting a new main task
            setComplianceReport(null);
        }
    };

    // Helper to extract headers (basic for CSV/JSON)
    const extractHeaders = (content, fileType) => {
        if (fileType.includes('csv') && content) {
            const lines = content.split('\n');
            if (lines.length > 0) {
                return lines[0].split(',').map(h => h.trim()).filter(h => h !== ''); // Filter out empty strings
            }
        } else if (fileType.includes('json') && content) {
            try {
                const parsed = JSON.parse(content);
                if (Array.isArray(parsed) && parsed.length > 0) {
                    return Object.keys(parsed[0]).filter(h => h !== '');
                } else if (typeof parsed === 'object' && parsed !== null) {
                    return Object.keys(parsed).filter(h => h !== '');
                }
            } catch (e) {
                console.error("Error parsing JSON for headers:", e);
            }
        }
        return [];
    };

    // Handle file upload for Dataset (CSV, JSON, or PDF data simulation)
    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        setDatasetFile(file);
        const mockDatasetId = `dataset_${Date.now()}`;
        setCurrentDatasetId(mockDatasetId);
        setIsProcessingFile(true); // Show loader for file processing

        if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
            // Simulate PDF text extraction for the dataset content
            const simulatedPdfDataText = `Simulated dataset content from PDF:
            Record 1: CustomerID: CUST001, OrderDate: 2023-01-15, Item: Laptop, Price: 1200.00, Email: customer1@example.com
            Record 2: CustomerID: CUST002, OrderDate: 2023-01-20, Item: Mouse, Price: 25.50, Email: customer2@example.com
            Record 3: CustomerID: CUST003, OrderDate: 2023-01-22, Item: Keyboard, Price: 75.00, Email: invalid-email-format
            Record 4: CustomerID: CUST001, OrderDate: 2023-01-25, Item: Monitor, Price: 300.00, Email: customer1@example.com
            Record 5: CustomerID: CUST004, OrderDate: 2023-01-28, Item: Webcam, Price: 50.00, Email: customer4@example.com
            This data contains personally identifiable information (PII) such as email addresses and customer IDs.
            Data elements present: CustomerID, OrderDate, Item, Price, Email.`;
            
            setUploadedDataContent(simulatedPdfDataText);
            const headers = extractHeaders(simulatedPdfDataText, 'text/plain'); // Try to extract headers from simulated text
            setDatasetHeaders(headers);

            const initialScore = Math.min(100, 50 + Math.floor(Math.random() * 50));
            setSimulatedDQResults(prev => ({ ...prev, overallQualityScore: initialScore }));
            displayModal("PDF Data Uploaded & Simulated", `PDF dataset "${file.name}" simulated. Initial estimated quality score: ${initialScore}%.`);
            setIsProcessingFile(false);

        } else {
            // For CSV/JSON, read as text as before
            const reader = new FileReader();
            reader.onload = (e) => {
                let content = e.target.result;
                setUploadedDataContent(content);

                const headers = extractHeaders(content, file.type);
                setDatasetHeaders(headers);

                const initialScore = Math.min(100, 50 + Math.floor(Math.random() * 50));
                setSimulatedDQResults(prev => ({ ...prev, overallQualityScore: initialScore }));
                displayModal("Data Uploaded", `Dataset "${file.name}" uploaded. Initial estimated quality score: ${initialScore}%.`);
                setIsProcessingFile(false);
            };
            reader.onerror = (e) => {
                console.error("Error reading file:", e);
                displayModal("File Read Error", "Failed to read the uploaded file.");
                setIsProcessingFile(false);
            };
            reader.readAsText(file);
        }
    };

    // Handle dimension checkbox change
    const handleDimensionChange = (event) => {
        const { value, checked } = event.target;
        setDqDimensions(prev =>
            checked ? [...prev, value] : prev.filter(dim => dim !== value)
        );
    };

    // Handle rule input change for a specific dimension/field
    const handleRuleInputChange = (dimension, field, value) => {
        setRules(prev => ({
            ...prev,
            [dimension]: {
                ...(prev[dimension] || {}),
                [field]: value
            }
        }));
    };

    // Save rules to Firestore
    const handleSaveRules = async () => {
        if (!db || !userId || !currentDatasetId) {
            console.error("Firestore not ready or dataset not selected.");
            displayModal("Save Error", "Firestore is not ready or no dataset has been selected.");
            return;
        }

        try {
            const rulesCollectionRef = collection(db, `artifacts/${__app_id}/users/${userId}/data_quality_rules`);
            await addDoc(rulesCollectionRef, {
                datasetId: currentDatasetId,
                dimensions: dqDimensions,
                definedRules: rules,
                timestamp: new Date(),
                status: 'defined'
            });
            displayModal("Success", "Rules saved successfully!");
            // Auto-advance: After saving, automatically move to "Run a Data Quality Check"
            setUserTaskChoice('Run a Data Quality Check');
        } catch (error) {
            console.error("Error saving rules to Firestore:", error);
            displayModal("Save Error", "Failed to save rules. Check console for details.");
        }
    };

    // Handle AI data analysis and rule recommendation
    const handleAnalyzeData = async () => {
        if (!uploadedDataContent) {
            displayModal("Analysis Error", "Please upload a dataset before attempting to analyze.");
            return;
        }

        setIsAnalyzing(true);
        setRecommendations([]);
        setSelectedRecommendations([]);
        // Do not clear dataElementDefinitions here, as it's a separate step (Identify CDEs)

        const prompt = `Act as a data quality expert. Analyze the following dataset snippet and identify potential data quality issues related to completeness (missing values), uniqueness (duplicate entries), validity (incorrect formats or values), and accuracy (values not matching expected references).

        For each identified issue, recommend a concrete data quality rule. Specify the dimension, the relevant column(s), and provide a concise suggestion for the rule. If possible, also provide an example of how this rule would look in a structured format (e.g., a regex pattern for validity, or example reference values for accuracy). Focus on identifying potential Core Data Elements (CDEs) and rules for them.

        Dataset Snippet:
        \`\`\`
        ${uploadedDataContent.substring(0, 5000)}
        \`\`\`
        (Only the first 5000 characters are provided for analysis, as large files can exceed token limits.)

        Provide your recommendations as a JSON array of objects. Each object should have the following properties:
        - \`dimension\` (string, e.g., "Completeness", "Uniqueness", "Validity", "Accuracy")
        - \`column\` (string, the name of the column affected, can be "N/A" if general or if specific column is not clear from snippet)
        - \`suggestion\` (string, a brief description of the recommended rule)
        - \`exampleRule\` (string, an example of the rule's parameter, e.g., a regex, a list of values, a field name)

        Example JSON structure:
        [
          {
            "dimension": "Completeness",
            "column": "email",
            "suggestion": "Ensure the 'email' column is not null.",
            "exampleRule": "email"
          },
          {
            "dimension": "Validity",
            "column": "date_format",
            "suggestion": "Validate 'date_format' follows формате-MM-DD pattern.",
            "exampleRule": "^\\\\d{4}-\\\\d{2}-\\\\d{2}$"
          }
        ]
        `;

        try {
            let chatHistory = [];
            chatHistory.push({ role: "user", parts: [{ text: prompt }] });
            const payload = {
                contents: chatHistory,
                generationConfig: {
                    responseMimeType: "application/json",
                    responseSchema: {
                        type: "ARRAY",
                        items: {
                            type: "OBJECT",
                            properties: {
                                "dimension": { "type": "STRING" },
                                "column": { "type": "STRING" },
                                "suggestion": { "type": "STRING" },
                                "exampleRule": { "type": "STRING" }
                            },
                            "propertyOrdering": ["dimension", "column", "suggestion", "exampleRule"]
                        }
                    }
                }
            };
            const apiKey = "";
            const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`;

            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            if (result.candidates && result.candidates.length > 0 &&
                result.candidates[0].content && result.candidates[0].content.parts &&
                result.candidates[0].content.parts.length > 0) {
                const jsonResponse = result.candidates[0].content.parts[0].text;
                try {
                    const parsedRecommendations = JSON.parse(jsonResponse);
                    setRecommendations(parsedRecommendations);
                    displayModal("Analysis Complete", "AI has generated data quality rule recommendations.");
                } catch (parseError) {
                    console.error("Error parsing AI response JSON:", parseError);
                    displayModal("AI Response Error", "AI generated an invalid JSON. Please check console for details.");
                }
            } else {
                console.error("AI did not return expected content:", result);
                displayModal("AI Response Error", "AI could not generate recommendations based on the data. Please try a different dataset or check the data format.");
            }
        } catch (error) {
            console.error("Error calling Gemini API:", error);
            displayModal("API Error", "Failed to connect to the AI service. Please try again later.");
        } finally {
            setIsAnalyzing(false);
        }
    };

    // Handle selection of a recommendation checkbox
    const handleRecommendationSelect = (index) => {
        setSelectedRecommendations(prev =>
            prev.includes(index) ? prev.filter(i => i !== index) : [...prev, index]
        );
    };

    // Apply selected recommendations to the 'Define Data Quality Rules' form
    const applySelectedRecommendations = () => {
        const newDqDimensions = new Set(dqDimensions);
        const newRules = { ...rules };

        selectedRecommendations.forEach(index => {
            const rec = recommendations[index];
            if (rec) {
                newDqDimensions.add(rec.dimension);

                switch (rec.dimension) {
                    case 'Completeness':
                        newRules.Completeness = {
                            fields: (newRules.Completeness?.fields ? newRules.Completeness.fields + ', ' : '') + rec.exampleRule
                        };
                        break;
                    case 'Uniqueness':
                        newRules.Uniqueness = {
                            fields: (newRules.Uniqueness?.fields ? newRules.Uniqueness.fields + ', ' : '') + rec.exampleRule
                        };
                        break;
                    case 'Validity':
                        newRules.Validity = {
                            field: rec.column,
                            pattern: rec.exampleRule
                        };
                        break;
                    case 'Accuracy':
                        newRules.Accuracy = {
                            field: rec.column,
                            referenceValues: (newRules.Accuracy?.referenceValues ? newRules.Accuracy.referenceValues + ', ' : '') + rec.exampleRule
                        };
                        break;
                    case 'Timeliness':
                        newRules.Timeliness = {
                            frequency: rec.exampleRule
                        };
                        break;
                    default:
                        console.warn(`Unknown dimension: ${rec.dimension}. Recommendation not applied.`);
                }
            }
        });

        setDqDimensions(Array.from(newDqDimensions));
        setRules(newRules);
        setUserTaskChoice('Define Data Quality Rules'); // Navigate to Define Rules
        setRecommendations([]);
        setSelectedRecommendations([]);
        displayModal("Recommendations Applied", "Selected recommendations have been pre-filled into 'Define Data Quality Rules'.");
    };

    // Handle getting field definitions (Identify CDEs)
    const handleGetFieldDefinitions = async () => {
        if (!uploadedDataContent) {
            displayModal("Error", "Please upload a dataset first to get field definitions.");
            return;
        }
        setIsDefiningFields(true);
        setDataElementDefinitions([]);

        const headerList = datasetHeaders.length > 0 ? `Headers: ${datasetHeaders.join(', ')}` : 'Headers are not explicitly provided. Infer data elements from the content.';

        const prompt = `Based on the following data snippet and potentially provided headers, identify and provide a concise definition for each Core Data Element (CDE). A CDE is a key piece of information that is critical to the business or regulatory function, regardless of its format (e.g., a column in a table, or a specific piece of information within unstructured text).
        Assume standard data types (e.g., 'string', 'integer', 'date') and common business contexts. Focus on identifying distinct, important data points.

        ${headerList}
        
        Dataset Snippet (first 1000 chars):
        \`\`\`
        ${uploadedDataContent.substring(0, 1000)}
        \`\`\`

        Provide your definitions as a JSON array of objects. Each object should have 'cdeName' (string, the identified Core Data Element name) and 'definition' (string, its concise explanation). If a data element cannot be clearly identified as a CDE or is not relevant, you can omit it.

        Example JSON structure:
        [
            {"cdeName": "customer_id", "definition": "Unique identifier for each customer, crucial for billing and support."},
            {"cdeName": "order_date", "definition": "Date when the customer's order was placed, important for revenue recognition and historical analysis."}
        ]
        `;

        try {
            let chatHistory = [];
            chatHistory.push({ role: "user", parts: [{ text: prompt }] });
            const payload = {
                contents: chatHistory,
                generationConfig: {
                    responseMimeType: "application/json",
                    responseSchema: {
                        type: "ARRAY",
                        items: {
                            type: "OBJECT",
                            properties: {
                                "cdeName": { "type": "STRING" },
                                "definition": { "type": "STRING" }
                            },
                            "propertyOrdering": ["cdeName", "definition"]
                        }
                    }
                }
            };
            const apiKey = "";
            const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`;

            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            if (result.candidates && result.candidates.length > 0 &&
                result.candidates[0].content && result.candidates[0].content.parts &&
                result.candidates[0].content.parts.length > 0) {
                const jsonResponse = result.candidates[0].content.parts[0].text;
                try {
                    const parsedDefinitions = JSON.parse(jsonResponse);
                    setDataElementDefinitions(parsedDefinitions);
                    displayModal("CDEs Identified", "AI has identified and defined Core Data Elements.");
                } catch (parseError) {
                    console.error("Error parsing AI response JSON for definitions:", parseError);
                    displayModal("AI Response Error", "AI generated an invalid JSON for CDE definitions. Check console.");
                }
            } else {
                console.error("AI did not return expected content for definitions:", result);
                displayModal("AI Response Error", "AI could not identify CDEs. Try again or check data format.");
            }
        } catch (error) {
            console.error("Error calling Gemini API for definitions:", error);
            displayModal("API Error", "Failed to connect to the AI service for CDE definitions. Please try again later.");
        } finally {
            setIsDefiningFields(false);
        }
    };


    // Simulate Data Quality Check execution
    const runSimulatedDQCheck = () => {
        if (!currentDatasetId || savedRules.length === 0) {
            displayModal("Validation Error", "Please upload a dataset and define/save some rules first.");
            return;
        }

        const totalRecords = 1000;
        const rulesToApply = savedRules.filter(ruleSet => {
            return ruleSet.datasetId === currentDatasetId;
        });

        let simulatedFailedRecords = [];
        let simulatedPassedCount = totalRecords;
        let rulesRun = 0;
        let cdeScores = []; // Array to store per-CDE scores

        // Initialize CDE scores (assuming datasetHeaders are our CDEs for simulation)
        // Ensure that CDE definitions are used if available, otherwise fallback to headers
        const cdeNames = dataElementDefinitions.length > 0 ? dataElementDefinitions.map(d => d.cdeName) : datasetHeaders;

        cdeNames.forEach(cdeName => {
            cdeScores.push({ cdeName: cdeName, score: 100, failedCount: 0 });
        });

        rulesToApply.forEach(ruleSet => {
            rulesRun++;
            const ruleDimensions = ruleSet.dimensions;

            // Helper to find and update CDE score
            const updateCDEscore = (cde, deduction) => {
                const cdeIndex = cdeScores.findIndex(s => s.cdeName === cde);
                if (cdeIndex !== -1) {
                    cdeScores[cdeIndex].score = Math.max(0, cdeScores[cdeIndex].score - deduction);
                    cdeScores[cdeIndex].failedCount++;
                }
            };

            // Simulate failures based on dimensions and rule fields if possible
            if (ruleDimensions.includes('Completeness')) {
                const fields = ruleSet.definedRules.Completeness?.fields?.split(',').map(f => f.trim()) || [];
                fields.forEach(field => {
                    if (Math.random() < 0.1) { // Simulate 10% chance of a field being incomplete
                        simulatedFailedRecords.push({
                            id: `ISSUE-${Math.floor(Math.random() * 10000)}`,
                            ruleFailed: `Completeness (${field || 'N/A'})`,
                            assignedTo: 'Unassigned',
                            status: 'Open',
                            recordId: `REC-${Math.floor(Math.random() * totalRecords)}`,
                            datasetId: currentDatasetId,
                            ruleId: ruleSet.id
                        });
                        simulatedPassedCount = Math.max(0, simulatedPassedCount - 5);
                        updateCDEscore(field, 5); // Deduct from CDE score
                    }
                });
            }
            if (ruleDimensions.includes('Uniqueness')) {
                const fields = ruleSet.definedRules.Uniqueness?.fields?.split(',').map(f => f.trim()) || [];
                fields.forEach(field => {
                    if (Math.random() < 0.05) { // Simulate 5% chance of a uniqueness issue
                        simulatedFailedRecords.push({
                            id: `ISSUE-${Math.floor(Math.random() * 10000)}`,
                            ruleFailed: `Uniqueness (${field || 'N/A'})`,
                            assignedTo: 'Unassigned',
                            status: 'Open',
                            recordId: `REC-${Math.floor(Math.random() * totalRecords)}`,
                            datasetId: currentDatasetId,
                            ruleId: ruleSet.id
                        });
                        simulatedPassedCount = Math.max(0, simulatedPassedCount - 3);
                        updateCDEscore(field, 3);
                    }
                });
            }
            if (ruleDimensions.includes('Validity')) {
                const field = ruleSet.definedRules.Validity?.field || 'N/A';
                if (Math.random() < 0.08) { // Simulate 8% chance of a validity issue
                    simulatedFailedRecords.push({
                        id: `ISSUE-${Math.floor(Math.random() * 10000)}`,
                        ruleFailed: `Validity (${field})`,
                        assignedTo: 'Unassigned',
                        status: 'Open',
                        recordId: `REC-${Math.floor(Math.random() * totalRecords)}`,
                        datasetId: currentDatasetId,
                        ruleId: ruleSet.id
                    });
                    simulatedPassedCount = Math.max(0, simulatedPassedCount - 7);
                    updateCDEscore(field, 7);
                }
            }
            if (ruleDimensions.includes('Accuracy')) {
                const field = ruleSet.definedRules.Accuracy?.field || 'N/A';
                 if (Math.random() < 0.07) { // Simulate 7% chance of an accuracy issue
                    simulatedFailedRecords.push({
                        id: `ISSUE-${Math.floor(Math.random() * 10000)}`,
                        ruleFailed: `Accuracy (${field})`,
                        assignedTo: 'Unassigned',
                        status: 'Open',
                        recordId: `REC-${Math.floor(Math.random() * totalRecords)}`,
                        datasetId: currentDatasetId,
                        ruleId: ruleSet.id
                    });
                    simulatedPassedCount = Math.max(0, simulatedPassedCount - 6);
                    updateCDEscore(field, 6);
                }
            }
             if (ruleDimensions.includes('Timeliness')) {
                const frequency = ruleSet.definedRules.Timeliness?.frequency || 'N/A';
                 if (Math.random() < 0.03) { // Simulate 3% chance of a timeliness issue
                    simulatedFailedRecords.push({
                        id: `ISSUE-${Math.floor(Math.random() * 10000)}`,
                        ruleFailed: `Timeliness (${frequency})`,
                        assignedTo: 'Unassigned',
                        status: 'Open',
                        recordId: `REC-${Math.floor(Math.random() * totalRecords)}`,
                        datasetId: currentDatasetId,
                        ruleId: ruleSet.id
                    });
                    simulatedPassedCount = Math.max(0, simulatedPassedCount - 2);
                    // Timeliness might affect all CDEs, or specific time-related CDEs.
                    // For simplicity, apply a small deduction to a random CDE if any exists.
                    if (cdeScores.length > 0) {
                        updateCDEscore(cdeScores[Math.floor(Math.random() * cdeScores.length)].cdeName, 2);
                    }
                }
            }
        });

        simulatedPassedCount = Math.min(totalRecords, simulatedPassedCount);
        const finalOverallQualityScore = (simulatedPassedCount / totalRecords) * 100;

        setSimulatedDQResults({
            overallQualityScore: finalOverallQualityScore,
            cdeQualityScores: cdeScores,
            testedRecords: totalRecords,
            passedRecords: simulatedPassedCount,
            failedRecords: simulatedFailedRecords,
            rulesRunCount: rulesRun
        });
        setUnresolvedIssues(simulatedFailedRecords);
        displayModal("Data Quality Check Complete", `Simulated check run. Found ${simulatedFailedRecords.length} issues. Go to 'Resolve Data Quality Issues' to manage them.`);
        // Auto-advance: After running DQ check, automatically move to "Resolve Data Quality Issues"
        setUserTaskChoice('Resolve Data Quality Issues');
    };

    // Handle resolving an issue
    const handleResolveIssue = (issueId) => {
        setUnresolvedIssues(prev => prev.filter(issue => issue.id !== issueId));
        displayModal("Issue Resolved", `Issue ${issueId} marked as resolved (simulated).`);
        // Note: In a real app, resolving an issue would also update the CDE quality scores
        // or trigger a re-run of the DQ check for affected data.
    };

    // Handle evaluating regulatory compliance
    const handleEvaluateCompliance = async () => {
        if (!uploadedDataContent || !regulatoryPolicyText) {
            displayModal("Compliance Error", "Please upload a dataset and provide regulatory policy text to evaluate compliance.");
            return;
        }

        setIsEvaluatingCompliance(true);
        setComplianceReport(null);

        // Include data element definitions in the prompt for richer context
        const cdeDefinitionsPrompt = dataElementDefinitions.length > 0
            ? `Identified Core Data Elements (CDEs) and their definitions in the dataset:
            ${dataElementDefinitions.map(d => `- ${d.cdeName}: ${d.definition}`).join('\n')}\n\n`
            : '';

        const prompt = `Act as a data governance and compliance expert. You will analyze a dataset snippet (and its identified Core Data Elements) and a regulatory policy text. Your task is to determine how well the dataset adheres to the given policy for autonomous compliance.

        First, identify any direct or implied requirements from the policy that apply to the data elements (columns/fields or CDEs) or their values. Consider aspects like data minimization, data retention, data accuracy, purpose limitation, security, and PII handling.
        Second, based on these requirements, the dataset snippet, and the identified CDEs, assess potential compliance issues or areas of non-compliance.
        Finally, provide a 'Compliance Score' out of 100, a list of identified compliance issues, and actionable recommendations to improve compliance. The recommendations should be practical steps.

        ${cdeDefinitionsPrompt}
        Dataset Headers: [${datasetHeaders.join(', ')}]

        Dataset Snippet (first 1000 chars):
        \`\`\`
        ${uploadedDataContent.substring(0, 1000)}
        \`\`\`

        Regulatory Policy Text:
        \`\`\`
        ${regulatoryPolicyText}
        \`\`\`

        Provide your response as a JSON object with the following properties:
        - \`complianceScore\` (integer, score out of 100)
        - \`complianceIssues\` (array of objects, each with \`issueDescription\` and \`suggestedAction\`)
        - \`complianceRecommendations\` (array of strings, general recommendations for improvement)

        Example JSON structure:
        {
          "complianceScore": 85,
          "complianceIssues": [
            {
              "issueDescription": "Customer names in the dataset appear to include full names, potentially violating data minimization for PII.",
              "suggestedAction": "Implement a policy to pseudonymize or tokenize customer names if full names are not strictly necessary for the processing purpose as per policy."
            }
          ],
          "complianceRecommendations": [
            "Review data retention policies against policy requirements.",
            "Ensure consent mechanisms are explicitly tied to data usage."
          ]
        }
        `;

        try {
            let chatHistory = [];
            chatHistory.push({ role: "user", parts: [{ text: prompt }] });
            const payload = {
                contents: chatHistory,
                generationConfig: {
                    responseMimeType: "application/json",
                    responseSchema: {
                        type: "OBJECT",
                        properties: {
                            "complianceScore": { "type": "NUMBER" },
                            "complianceIssues": {
                                "type": "ARRAY",
                                "items": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "issueDescription": { "type": "STRING" },
                                        "suggestedAction": { "type": "STRING" }
                                    }
                                }
                            },
                            "complianceRecommendations": {
                                "type": "ARRAY",
                                "items": { "type": "STRING" }
                            }
                        },
                        "propertyOrdering": ["complianceScore", "complianceIssues", "complianceRecommendations"]
                    }
                }
            };
            const apiKey = "";
            const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`;

            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            if (result.candidates && result.candidates.length > 0 &&
                result.candidates[0].content && result.candidates[0].content.parts &&
                result.candidates[0].content.parts.length > 0) {
                const jsonResponse = result.candidates[0].content.parts[0].text;
                try {
                    const parsedReport = JSON.parse(jsonResponse);
                    setComplianceReport(parsedReport);
                    displayModal("Compliance Evaluation Complete", "AI has generated the policy compliance report.");

                    const complianceReportsCollection = collection(db, `artifacts/${__app_id}/users/${userId}/regulatory_compliance_reports`);
                    await addDoc(complianceReportsCollection, {
                        datasetId: currentDatasetId,
                        policyText: regulatoryPolicyText,
                        report: parsedReport,
                        timestamp: new Date()
                    });

                    // Auto-advance: After compliance evaluation, automatically move to "View Quality Dashboard"
                    setUserTaskChoice('View Quality Dashboard');

                } catch (parseError) {
                    console.error("Error parsing AI compliance report JSON:", parseError);
                    displayModal("AI Response Error", "AI generated an invalid JSON for compliance report. Check console for details.");
                }
            } else {
                console.error("AI did not return expected compliance report:", result);
                displayModal("AI Response Error", "AI could not generate compliance report. Please refine policy or data.");
            }
        } catch (error) {
            console.error("Error calling Gemini API for compliance:", error);
            displayModal("API Error", "Failed to connect to the AI service for compliance. Please try again later.");
        } finally {
            setIsEvaluatingCompliance(false);
        }
    };


    // Handle file upload for Regulatory Policy (PDF only)
    const handlePolicyFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        setIsProcessingFile(true); // Show loader

        if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
            // Simulate PDF text extraction for the policy document
            const simulatedPolicyText = `Simulated Regulatory Policy Document (GDPR Snippet):
            Article 5: Principles relating to processing of personal data.
            Personal data shall be:
            (a) processed lawfully, fairly and in a transparent manner in relation to the data subject (‘lawfulness, fairness and transparency’);
            (b) collected for specified, explicit and legitimate purposes and not further processed in a manner that is incompatible with those purposes (‘purpose limitation’);
            (c) adequate, relevant and limited to what is necessary in relation to the purposes for which they are processed (‘data minimisation’);
            (d) accurate and, where necessary, kept up to date; every reasonable step must be taken to ensure that personal data that are inaccurate, having regard to the purposes for which they are processed, are erased or rectified without delay (‘accuracy’);
            (e) kept in a form which permits identification of data subjects for no longer than is necessary for the purposes for which the personal data are processed (‘storage limitation’);
            (f) processed in a manner that ensures appropriate security of the personal data, including protection against unauthorised or unlawful processing and against accidental loss, destruction or damage, using appropriate technical or organisational measures (‘integrity and confidentiality’).
            
            This policy also states that all customer email addresses must be validated for format and domain legitimacy.
            Sensitive personal data (e.g., health information) should be explicitly consented to by the data subject and stored separately with enhanced encryption.`;
            
            setRegulatoryPolicyText(simulatedPolicyText);
            displayModal("Policy PDF Processed", `Policy PDF "${file.name}" simulated. Its content is now available for compliance evaluation.`);
            setIsProcessingFile(false);
        } else {
            displayModal("Unsupported File Type", "Only PDF files are supported for policy upload. Please upload a PDF.");
            setIsProcessingFile(false);
            event.target.value = null; // Clear file input
        }
    };

    // Handle export report
    const handleExportReport = () => {
        const reportData = {
            overallDataQualityScore: simulatedDQResults.overallQualityScore,
            cdeQualityScores: simulatedDQResults.cdeQualityScores,
            lastDataQualityCheck: {
                testedRecords: simulatedDQResults.testedRecords,
                passedRecords: simulatedDQResults.passedRecords,
                failedRulesCount: simulatedDQResults.failedRecords.length,
                rulesRunCount: simulatedDQResults.rulesRunCount
            },
            unresolvedIssues: unresolvedIssues,
            dataElementDefinitions: dataElementDefinitions,
            regulatoryComplianceReport: complianceReport,
            timestamp: new Date().toISOString()
        };

        const jsonString = JSON.stringify(reportData, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `data_governance_report_${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        displayModal("Export Successful", "Data Governance Report exported as JSON.");
    };


    // Render logic based on user task choice
    const renderContent = () => {
        switch (userTaskChoice) {
            case 'Define Data Quality Rules':
                return (
                    <div className="space-y-6">
                        <h2 className="text-2xl font-semibold text-gray-800">Define Data Quality Rules</h2>

                        {/* Display uploaded dataset info if available */}
                        {datasetFile && (
                            <div className="bg-white p-6 rounded-lg shadow">
                                <h3 className="text-xl font-semibold text-gray-800 mb-4">Current Dataset: {datasetFile.name}</h3>
                                {dataElementDefinitions.length > 0 ? (
                                     <p className="mt-2 text-sm text-gray-600">Identified CDEs: <span className="font-semibold">{dataElementDefinitions.map(d => d.cdeName).join(', ')}</span></p>
                                ) : datasetHeaders.length > 0 ? (
                                     <p className="mt-2 text-sm text-gray-600">Detected Headers: <span className="font-semibold">{datasetHeaders.join(', ')}</span></p>
                                ) : (
                                    <p className="mt-2 text-sm text-gray-600">No CDEs/headers identified yet. Run "Identify CDEs and Define them".</p>
                                )}
                            </div>
                        )}

                        {/* Choose Quality Dimensions */}
                        {datasetFile && (
                            <div className="bg-white p-6 rounded-lg shadow">
                                <label className="block text-gray-700 text-lg font-medium mb-2">Choose Quality Dimensions</label>
                                <div className="grid grid-cols-2 gap-4">
                                    {['Completeness', 'Accuracy', 'Timeliness', 'Uniqueness', 'Validity'].map(dim => (
                                        <div key={dim} className="flex items-center">
                                            <input
                                                type="checkbox"
                                                id={dim}
                                                value={dim}
                                                checked={dqDimensions.includes(dim)}
                                                onChange={handleDimensionChange}
                                                className="form-checkbox h-5 w-5 text-indigo-600 rounded-md"
                                            />
                                            <label htmlFor={dim} className="ml-2 text-gray-700">{dim}</label>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Define Rules per Dimension */}
                        {dqDimensions.length > 0 && datasetFile && (
                            <div className="bg-white p-6 rounded-lg shadow">
                                <h3 className="text-xl font-semibold text-gray-800 mb-4">Define Rules per Dimension</h3>
                                {dqDimensions.map(dim => (
                                    <div key={dim} className="mb-6 p-4 border border-gray-200 rounded-md">
                                        <h4 className="text-lg font-medium text-indigo-700 mb-3">{dim}</h4>
                                        {dim === 'Completeness' && (
                                            <div>
                                                <label htmlFor="completeness-fields" className="block text-gray-700 text-sm font-medium mb-1">
                                                    List the field(s) that must NOT be null (comma-separated):
                                                </label>
                                                <input
                                                    type="text"
                                                    id="completeness-fields"
                                                    value={rules.Completeness?.fields || ''}
                                                    onChange={(e) => handleRuleInputChange('Completeness', 'fields', e.target.value)}
                                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                                                    placeholder="e.g., 'customer_id, order_date'"
                                                />
                                            </div>
                                        )}
                                        {dim === 'Uniqueness' && (
                                            <div>
                                                <label htmlFor="uniqueness-fields" className="block text-gray-700 text-sm font-medium mb-1">
                                                    Enter the fields that must be unique (comma-separated):
                                                </label>
                                                <input
                                                    type="text"
                                                    id="uniqueness-fields"
                                                    value={rules.Uniqueness?.fields || ''}
                                                    onChange={(e) => handleRuleInputChange('Uniqueness', 'fields', e.target.value)}
                                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                                                    placeholder="e.g., 'product_sku'"
                                                />
                                            </div>
                                        )}
                                        {dim === 'Timeliness' && (
                                            <div>
                                                <label htmlFor="timeliness-frequency" className="block text-gray-700 text-sm font-medium mb-1">
                                                    Enter expected update frequency:
                                                </label>
                                                <select
                                                    id="timeliness-frequency"
                                                    value={rules.Timeliness?.frequency || ''}
                                                    onChange={(e) => handleRuleInputChange('Timeliness', 'frequency', e.target.value)}
                                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                                                >
                                                    <option value="">Select frequency</option>
                                                    <option value="Daily">Daily</option>
                                                    <option value="Weekly">Weekly</option>
                                                    <option value="Monthly">Monthly</option>
                                                    <option value="Hourly">Hourly</option>
                                                </select>
                                            </div>
                                        )}
                                        {dim === 'Validity' && (
                                            <div className="space-y-2">
                                                <div>
                                                    <label htmlFor={`validity-field-${dim}`} className="block text-gray-700 text-sm font-medium mb-1">
                                                        Specify the field:
                                                    </label>
                                                    <input
                                                        type="text"
                                                        id={`validity-field-${dim}`}
                                                        value={rules.Validity?.field || ''}
                                                        onChange={(e) => handleRuleInputChange('Validity', 'field', e.target.value)}
                                                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                                                        placeholder="e.g., 'email'"
                                                    />
                                                </div>
                                                <div>
                                                    <label htmlFor={`validity-pattern-${dim}`} className="block text-gray-700 text-sm font-medium mb-1">
                                                        Valid values (comma-separated) or regex pattern:
                                                    </label>
                                                    <input
                                                        type="text"
                                                        id={`validity-pattern-${dim}`}
                                                        value={rules.Validity?.pattern || ''}
                                                        onChange={(e) => handleRuleInputChange('Validity', 'pattern', e.target.value)}
                                                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                                                        placeholder="e.g., 'active, inactive' or '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'"
                                                    />
                                                </div>
                                            </div>
                                        )}
                                        {dim === 'Accuracy' && (
                                            <div className="space-y-2">
                                                <div>
                                                    <label htmlFor={`accuracy-field-${dim}`} className="block text-gray-700 text-sm font-medium mb-1">
                                                        Specify the field:
                                                    </label>
                                                    <input
                                                        type="text"
                                                        id={`accuracy-field-${dim}`}
                                                        value={rules.Accuracy?.field || ''}
                                                        onChange={(e) => handleRuleInputChange('Accuracy', 'field', e.target.value)}
                                                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                                                        placeholder="e.g., 'country_code'"
                                                    />
                                                </div>
                                                <div>
                                                    <label htmlFor={`accuracy-ref-values-${dim}`} className="block text-gray-700 text-sm font-medium mb-1">
                                                        Reference values (comma-separated):
                                                    </label>
                                                    <input
                                                        type="text"
                                                        id={`accuracy-ref-values-${dim}`}
                                                        value={rules.Accuracy?.referenceValues || ''}
                                                        onChange={(e) => handleRuleInputChange('Accuracy', 'referenceValues', e.target.value)}
                                                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                                                        placeholder="e.g., 'USA, CAN, MEX'"
                                                    />
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                ))}
                                <button
                                    onClick={handleSaveRules}
                                    className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded-lg shadow-md transition duration-300 ease-in-out transform hover:scale-105"
                                >
                                    Save Rules
                                </button>
                            </div>
                        )}
                    </div>
                );
            case 'Run a Data Quality Check':
                return (
                    <div className="space-y-6">
                        <h2 className="text-2xl font-semibold text-gray-800">6. Run a Data Quality Check</h2>
                        <div className="bg-white p-6 rounded-lg shadow">
                            <p className="text-gray-700">Please select a dataset and the rules you'd like to validate.</p>
                            <div className="mt-4">
                                <label htmlFor="dataset-select" className="block text-gray-700 text-sm font-medium mb-1">Currently Selected Dataset:</label>
                                <select
                                    id="dataset-select"
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                                    value={currentDatasetId || ''}
                                    onChange={(e) => setCurrentDatasetId(e.target.value)}
                                    disabled={!currentDatasetId} // Disable if no dataset is loaded
                                >
                                    {currentDatasetId ? (
                                        <option value={currentDatasetId}>{datasetFile?.name || `Dataset ${currentDatasetId.substring(0, 8)}...`}</option>
                                    ) : (
                                        <option value="">No dataset uploaded. Please upload data first.</option>
                                    )}
                                </select>
                            </div>

                            <div className="mt-4">
                                <label className="block text-gray-700 text-sm font-medium mb-2">Selected Rules to Run:</label>
                                <div className="space-y-2 max-h-48 overflow-y-auto border p-2 rounded-md bg-gray-50">
                                    {savedRules.length > 0 && currentDatasetId ? (
                                        savedRules.filter(ruleSet => ruleSet.datasetId === currentDatasetId).map(ruleSet => (
                                            <div key={ruleSet.id} className="flex items-center">
                                                <input
                                                    type="checkbox"
                                                    id={`rule-${ruleSet.id}`}
                                                    value={ruleSet.id}
                                                    defaultChecked // For simplicity, assume all rules for current dataset are selected
                                                    className="form-checkbox h-4 w-4 text-green-600 rounded"
                                                />
                                                <label htmlFor={`rule-${ruleSet.id}`} className="ml-2 text-gray-700">
                                                    Rules for Dataset: {ruleSet.datasetId || 'N/A'} (Dimensions: {ruleSet.dimensions.join(', ')})
                                                </label>
                                            </div>
                                        ))
                                    ) : (
                                        <p className="text-gray-500 text-sm">No rules defined or no dataset selected yet.</p>
                                    )}
                                </div>
                            </div>

                            <button
                                onClick={runSimulatedDQCheck}
                                disabled={!currentDatasetId || savedRules.length === 0}
                                className={`mt-6 w-full ${currentDatasetId && savedRules.length > 0 ? 'bg-green-600 hover:bg-green-700' : 'bg-green-400 cursor-not-allowed'} text-white font-bold py-2 px-4 rounded-lg shadow-md transition duration-300 ease-in-out transform hover:scale-105`}
                            >
                                Execute Validation
                            </button>
                            {simulatedDQResults.testedRecords > 0 && (
                                <div className="mt-4 p-4 bg-gray-50 rounded-md border text-sm">
                                    <h3 className="font-semibold text-gray-800">Last Check Results:</h3>
                                    <p>Records Tested: <span className="font-bold">{simulatedDQResults.testedRecords}</span></p>
                                    <p>Records Passed: <span className="font-bold">{simulatedDQResults.passedRecords}</span></p>
                                    <p>Failed Rules Found: <span className="font-bold">{simulatedDQResults.failedRecords.length}</span></p>
                                    <p>Simulated Overall Quality Score: <span className="font-bold text-green-700">{simulatedDQResults.overallQualityScore.toFixed(2)}%</span></p>
                                </div>
                            )}

                            <button
                                onClick={handleExportReport}
                                className="mt-4 w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg shadow-md transition duration-300 ease-in-out transform hover:scale-105"
                            >
                                Export Current Report
                            </button>
                        </div>
                    </div>
                );
            case 'View Quality Dashboard':
                const totalFailed = simulatedDQResults.failedRecords.length;
                const totalResolved = simulatedDQResults.failedRecords.length - unresolvedIssues.length;
                const totalUnresolved = unresolvedIssues.length;

                const overallPassPercentage = simulatedDQResults.testedRecords > 0
                    ? ((simulatedDQResults.testedRecords - totalUnresolved) / simulatedDQResults.testedRecords) * 100
                    : simulatedDQResults.overallQualityScore;

                return (
                    <div className="space-y-6">
                        <h2 className="text-2xl font-semibold text-gray-800">8. Your Data Quality Summary Dashboard</h2>
                        <div className="bg-white p-6 rounded-lg shadow">
                            <p className="text-gray-700 mb-4">Here's a quick look at the current Data Quality metrics and compliance status.</p>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                                <div className="border p-4 rounded-md bg-blue-50 text-center">
                                    <h3 className="font-semibold text-lg text-blue-800">Overall Data Quality Score</h3>
                                    <p className="text-4xl font-bold text-blue-900 mt-2">{overallPassPercentage.toFixed(2)}%</p>
                                </div>
                                <div className="border p-4 rounded-md bg-yellow-50 text-center">
                                    <h3 className="font-semibold text-lg text-yellow-800">Total Issues Found</h3>
                                    <p className="text-4xl font-bold text-yellow-900 mt-2">{totalFailed}</p>
                                </div>
                            </div>

                            {complianceReport && (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
                                    <div className="border p-4 rounded-md bg-green-50 text-center">
                                        <h3 className="font-semibold text-lg text-green-800">Policy Compliance Score</h3>
                                        <p className="text-4xl font-bold text-green-900">{complianceReport.complianceScore}%</p>
                                    </div>
                                    <div className="border p-4 rounded-md bg-red-50 text-center">
                                        <h3 className="font-semibold text-lg text-red-800">Compliance Issues</h3>
                                        <p className="text-4xl font-bold text-red-900">{complianceReport.complianceIssues.length}</p>
                                    </div>
                                </div>
                            )}

                            <div className="mt-4 space-y-4">
                                <div className="border p-4 rounded-md bg-gray-50">
                                    <h3 className="font-semibold text-lg">Issue Status Summary</h3>
                                    <p className="text-sm text-gray-600">Total Resolved: <span className="font-bold text-green-700">{totalResolved}</span></p>
                                    <p className="text-sm text-gray-600">Total Unresolved: <span className="font-bold text-red-700">{totalUnresolved}</span></p>
                                    <p className="text-sm text-gray-600 mt-2">
                                        Pie chart: Pass vs Fail % - Placeholder for chart visualization (e.g., using Recharts).
                                    </p>
                                </div>
                                {simulatedDQResults.cdeQualityScores.length > 0 && (
                                    <div className="border p-4 rounded-md bg-gray-50">
                                        <h3 className="font-semibold text-lg">6. Quality Scores per Data Element (CDE)</h3>
                                        <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                                            {simulatedDQResults.cdeQualityScores.map((cde, index) => (
                                                <div key={index} className="p-3 bg-white border border-gray-200 rounded-md shadow-sm">
                                                    <p className="text-md font-semibold text-gray-800">{cde.cdeName}</p>
                                                    <p className={`text-xl font-bold ${cde.score > 80 ? 'text-green-600' : cde.score > 60 ? 'text-yellow-600' : 'text-red-600'}`}>
                                                        {cde.score.toFixed(1)}%
                                                    </p>
                                                    {cde.failedCount > 0 && <p className="text-xs text-gray-500">({cde.failedCount} issues)</p>}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                <div className="border p-4 rounded-md bg-gray-50">
                                    <h3 className="font-semibold text-lg">Rule Failures by Type (Simulated)</h3>
                                    <p className="text-sm text-gray-600">Placeholder for bar chart visualization. Would show counts of completeness, uniqueness, etc., issues.</p>
                                </div>
                                <div className="border p-4 rounded-md bg-gray-50">
                                    <h3 className="font-semibold text-lg">Trend Over Time (Placeholder)</h3>
                                    <p className="text-sm text-gray-600">Placeholder for line chart visualization, showing quality trends over multiple runs.</p>
                                </div>
                                <div className="border p-4 rounded-md bg-gray-50">
                                    <h3 className="font-semibold text-lg">Failed Records Table (Summary)</h3>
                                    <p className="text-sm text-gray-600">
                                        This table would summarize key failed records or link to the 'Resolve Issues' section for details.
                                    </p>
                                </div>
                                <div className="border p-4 rounded-md bg-gray-50">
                                    <h3 className="font-semibold text-lg">Filters (Placeholder)</h3>
                                    <p className="text-sm text-gray-600">Dataset, Date range, Rule type (Placeholder for filter controls)</p>
                                </div>
                            </div>
                        </div>
                    </div>
                );
            case 'Resolve Data Quality Issues':
                return (
                    <div className="space-y-6">
                        <h2 className="text-2xl font-semibold text-gray-800">Resolve Data Quality Issues</h2>
                        <div className="bg-white p-6 rounded-lg shadow">
                            <p className="text-gray-700">Here are unresolved issues from your recent data quality checks. You can assign, comment on, and mark them as resolved.</p>
                            <div className="mt-4 overflow-x-auto">
                                <table className="min-w-full bg-white border border-gray-300 rounded-lg">
                                    <thead>
                                        <tr>
                                            <th className="py-2 px-4 border-b text-left text-gray-600 font-semibold">Record ID</th>
                                            <th className="py-2 px-4 border-b text-left text-gray-600 font-semibold">Rule Failed</th>
                                            <th className="py-2 px-4 border-b text-left text-gray-600 font-semibold">Assigned To</th>
                                            <th className="py-2 px-4 border-b text-left text-gray-600 font-semibold">Status</th>
                                            <th className="py-2 px-4 border-b text-left text-gray-600 font-semibold">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {unresolvedIssues.length > 0 ? (
                                            unresolvedIssues.map(issue => (
                                                <tr key={issue.id}>
                                                    <td className="py-2 px-4 border-b text-gray-800">{issue.recordId}</td>
                                                    <td className="py-2 px-4 border-b text-gray-800">{issue.ruleFailed}</td>
                                                    <td className="py-2 px-4 border-b text-gray-800">{issue.assignedTo}</td>
                                                    <td className="py-2 px-4 border-b text-gray-800">{issue.status}</td>
                                                    <td className="py-2 px-4 border-b text-gray-800">
                                                        <button className="text-indigo-600 hover:text-indigo-900 mr-2">Assign</button>
                                                        <button className="text-blue-600 hover:text-blue-900 mr-2">Comment</button>
                                                        <button
                                                            onClick={() => handleResolveIssue(issue.id)}
                                                            className="text-green-600 hover:text-green-900"
                                                        >
                                                            Resolve
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))
                                        ) : (
                                            <tr>
                                                <td colSpan="5" className="py-4 px-4 text-center text-gray-500">No unresolved issues found. Run a Data Quality Check first!</td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                            <button
                                onClick={() => displayModal("Coming Soon", "Simulating re-running validation for selected issues... This will re-evaluate data based on updated rules or resolutions.")}
                                className="mt-6 w-full bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded-lg shadow-md transition duration-300 ease-in-out transform hover:scale-105"
                            >
                                Re-run Validation
                            </button>
                        </div>
                    </div>
                );
            case 'Analyze Data & Recommend Rules':
                return (
                    <div className="space-y-6">
                        <h2 className="text-2xl font-semibold text-gray-800">1. Upload Data & Analyze Data</h2>

                        {/* Upload Data for Analysis */}
                        <div className="bg-white p-6 rounded-lg shadow">
                            <label className="block text-gray-700 text-lg font-medium mb-2">Upload Dataset for AI Analysis (CSV, JSON, or PDF)</label>
                            <input
                                type="file"
                                accept=".csv,.json,.pdf"
                                onChange={handleFileUpload}
                                className="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none"
                            />
                            {isProcessingFile && (
                                <p className="mt-2 text-sm text-blue-600 flex items-center">
                                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Processing file...
                                </p>
                            )}
                            {datasetFile && !isProcessingFile && (
                                <p className="mt-2 text-sm text-gray-600">Selected file: {datasetFile.name}</p>
                            )}
                            {!datasetFile && !isProcessingFile && (
                                <p className="mt-2 text-sm text-red-500">Please upload a dataset to analyze.</p>
                            )}
                            {uploadedDataContent && (
                                <div className="mt-4 p-3 bg-gray-50 border rounded-md text-sm text-gray-700 overflow-auto max-h-48">
                                    <p className="font-semibold mb-1">Preview of uploaded data content:</p>
                                    <pre className="whitespace-pre-wrap break-words">{uploadedDataContent.substring(0, 500)}...</pre>
                                </div>
                            )}

                            {datasetHeaders.length > 0 && (
                                <div className="mt-4 p-3 bg-indigo-50 border border-indigo-200 rounded-md text-sm text-white">
                                    <p className="font-semibold mb-1">Simulated Initial Data Quality Score: <span className="text-xl font-bold">{simulatedDQResults.overallQualityScore.toFixed(2)}%</span></p>
                                    <p className="font-semibold mb-2">Detected Headers (Potential CDEs): <span className="font-normal">{datasetHeaders.join(', ')}</span></p>
                                </div>
                            )}

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
                                <button
                                    onClick={handleAnalyzeData}
                                    disabled={!uploadedDataContent || isAnalyzing}
                                    className={`w-full ${uploadedDataContent && !isAnalyzing ? 'bg-blue-600 hover:bg-blue-700' : 'bg-blue-400 cursor-not-allowed'} text-white font-bold py-2 px-4 rounded-lg shadow-md transition duration-300 ease-in-out transform hover:scale-105`}
                                >
                                    {isAnalyzing ? (
                                        <span className="flex items-center justify-center">
                                            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                            </svg>
                                            Analyzing Data...
                                        </span>
                                    ) : (
                                        '3. Analyze Data & Get Recommendations'
                                    )}
                                </button>

                                <button
                                    onClick={handleGetFieldDefinitions}
                                    disabled={!uploadedDataContent || isDefiningFields}
                                    className={`w-full ${uploadedDataContent && !isDefiningFields ? 'bg-purple-600 hover:bg-purple-700' : 'bg-purple-400 cursor-not-allowed'} text-white font-bold py-2 px-4 rounded-lg shadow-md transition duration-300 ease-in-out transform hover:scale-105`}
                                >
                                    {isDefiningFields ? (
                                        <span className="flex items-center justify-center">
                                            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                            </svg>
                                            Getting Definitions...
                                        </span>
                                    ) : (
                                        '4. Identify CDEs and Define them'
                                    )}
                                </button>
                            </div>
                        </div>

                        {/* Display Data Element Definitions */}
                        {dataElementDefinitions.length > 0 && (
                            <div className="bg-white p-6 rounded-lg shadow">
                                <h3 className="text-xl font-semibold text-gray-800 mb-4">Identified Core Data Elements (CDEs):</h3>
                                <div className="space-y-3">
                                    {dataElementDefinitions.map((def, index) => (
                                        <div key={index} className="p-3 border border-gray-200 rounded-md bg-blue-50">
                                            <p className="text-md font-semibold text-blue-800">{def.cdeName}</p>
                                            <p className="text-gray-700 text-sm mt-1">{def.definition}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Display AI Recommendations */}
                        {recommendations.length > 0 && (
                            <div className="bg-white p-6 rounded-lg shadow">
                                <h3 className="text-xl font-semibold text-gray-800 mb-4">5. Recommended Data Quality Rules on Identified CDEs:</h3>
                                <div className="space-y-4">
                                    {recommendations.map((rec, index) => (
                                        <div key={index} className="p-4 border border-gray-200 rounded-md bg-gray-50 flex items-start">
                                            <input
                                                type="checkbox"
                                                checked={selectedRecommendations.includes(index)}
                                                onChange={() => handleRecommendationSelect(index)}
                                                className="form-checkbox h-5 w-5 text-green-600 rounded-md mt-1 mr-3"
                                            />
                                            <div className="flex-1">
                                                <p className="text-sm font-semibold text-indigo-700">{rec.dimension} - CDE/Column: {rec.column}</p>
                                                <p className="text-gray-800 mt-1">{rec.suggestion}</p>
                                                {rec.exampleRule && (
                                                    <p className="text-xs text-gray-600 mt-2">Example Rule Parameter: <code className="bg-gray-200 p-1 rounded text-sm">{rec.exampleRule}</code></p>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                <button
                                    onClick={applySelectedRecommendations}
                                    disabled={selectedRecommendations.length === 0}
                                    className={`mt-6 w-full ${selectedRecommendations.length > 0 ? 'bg-indigo-500 hover:bg-indigo-600' : 'bg-indigo-300 cursor-not-allowed'} text-white font-bold py-2 px-4 rounded-lg shadow-md transition duration-300 ease-in-out transform hover:scale-105`}
                                >
                                    Apply Selected Rules on CDEs (to Define Rules section)
                                </button>
                            </div>
                        )}
                    </div>
                );
            case 'Manage Regulatory Compliance':
                return (
                    <div className="space-y-6">
                        <h2 className="text-2xl font-semibold text-gray-800">2. Manage Regulatory Compliance</h2>
                        <div className="bg-white p-6 rounded-lg shadow">
                            <p className="text-gray-700 mb-4">First, upload your dataset via "Analyze Data & Recommend Rules". Then, provide or upload your regulatory policy.</p>

                            <label htmlFor="policy-file" className="block text-gray-700 text-lg font-medium mb-2">
                                Upload Regulatory Policy (PDF Document)
                            </label>
                            <input
                                type="file"
                                id="policy-file"
                                accept=".pdf"
                                onChange={handlePolicyFileUpload}
                                className="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none"
                            />
                             {isProcessingFile && (
                                <p className="mt-2 text-sm text-blue-600 flex items-center">
                                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Processing policy file...
                                </p>
                            )}
                            {regulatoryPolicyText && (
                                <div className="mt-4 p-3 bg-gray-50 border rounded-md text-sm text-gray-700 overflow-auto max-h-48">
                                    <p className="font-semibold mb-1">Preview of policy text:</p>
                                    <pre className="whitespace-pre-wrap break-words">{regulatoryPolicyText.substring(0, 500)}...</pre>
                                </div>
                            )}

                            <label htmlFor="policy-text-manual" className="block text-gray-700 text-lg font-medium mt-6 mb-2">
                                Or manually enter Regulatory Policy Text
                            </label>
                            <textarea
                                id="policy-text-manual"
                                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-green-500 focus:ring-green-500 h-48 p-3 resize-y"
                                placeholder="Paste your regulatory policy text here..."
                                value={regulatoryPolicyText}
                                onChange={(e) => setRegulatoryPolicyText(e.target.value)}
                            ></textarea>

                            <button
                                onClick={handleEvaluateCompliance}
                                disabled={!uploadedDataContent || !regulatoryPolicyText || isEvaluatingCompliance}
                                className={`mt-6 w-full ${uploadedDataContent && regulatoryPolicyText && !isEvaluatingCompliance ? 'bg-green-600 hover:bg-green-700' : 'bg-green-400 cursor-not-allowed'} text-white font-bold py-2 px-4 rounded-lg shadow-md transition duration-300 ease-in-out transform hover:scale-105`}
                            >
                                {isEvaluatingCompliance ? (
                                    <span className="flex items-center justify-center">
                                        <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        Evaluating Compliance...
                                    </span>
                                ) : (
                                    'Evaluate Policy Compliance'
                                )}
                            </button>
                        </div>

                        {complianceReport && (
                            <div className="bg-white p-6 rounded-lg shadow">
                                <h3 className="text-xl font-semibold text-gray-800 mb-4">Compliance Report:</h3>
                                <div className="p-3 mb-4 rounded-md border-2 border-green-500 bg-green-50 text-center">
                                    <p className="text-lg font-semibold text-green-800">Compliance Score:</p>
                                    <p className="text-5xl font-bold text-green-900">{complianceReport.complianceScore}%</p>
                                </div>

                                {complianceReport.complianceIssues.length > 0 && (
                                    <div className="mb-4">
                                        <h4 className="text-lg font-semibold text-red-700 mb-2">Identified Issues:</h4>
                                        <ul className="list-disc list-inside space-y-2">
                                            {complianceReport.complianceIssues.map((issue, index) => (
                                                <li key={index} className="text-gray-800">
                                                    <strong>{issue.issueDescription}</strong>: {issue.suggestedAction}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}

                                {complianceReport.complianceRecommendations.length > 0 && (
                                    <div>
                                        <h4 className="text-lg font-semibold text-blue-700 mb-2">Recommendations for Improvement:</h4>
                                        <ul className="list-disc list-inside space-y-2">
                                            {complianceReport.complianceRecommendations.map((rec, index) => (
                                                <li key={index} className="text-gray-800">{rec}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                );
            case 'Go to Home':
                setUserTaskChoice('');
                return null;
            case 'Exit':
                return (
                    <div className="text-center p-8">
                        <p className="text-xl text-gray-700">Thank you for using the Data Quality Assistant!</p>
                    </div>
                );
            default:
                return (
                    <div className="space-y-6">
                        <h2 className="text-2xl font-semibold text-gray-800">Welcome to Data Quality Assistant</h2>
                        <p className="text-gray-700 mb-4">Hi! I'm your Data Quality Assistant. What would you like to do today?</p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <button
                                onClick={() => handleMainMenuClick('Analyze Data & Recommend Rules')}
                                className="bg-blue-500 hover:bg-blue-600 text-white font-bold py-3 px-6 rounded-lg shadow-lg transition duration-300 ease-in-out transform hover:scale-105"
                            >
                                1. Upload Data & Analyze
                            </button>
                            <button
                                onClick={() => handleMainMenuClick('Manage Regulatory Compliance')}
                                className="bg-teal-500 hover:bg-teal-600 text-white font-bold py-3 px-6 rounded-lg shadow-lg transition duration-300 ease-in-out transform hover:scale-105"
                            >
                                2. Manage Regulatory Compliance
                            </button>
                            <button
                                onClick={() => handleMainMenuClick('Define Data Quality Rules')}
                                className="bg-indigo-500 hover:bg-indigo-600 text-white font-bold py-3 px-6 rounded-lg shadow-lg transition duration-300 ease-in-out transform hover:scale-105"
                            >
                                5. Define Data Quality Rules
                            </button>
                             <button
                                onClick={() => handleMainMenuClick('Run a Data Quality Check')}
                                className="bg-green-500 hover:bg-green-600 text-white font-bold py-3 px-6 rounded-lg shadow-lg transition duration-300 ease-in-out transform hover:scale-105"
                            >
                                6. Run Data Quality Check
                            </button>
                            <button
                                onClick={() => handleMainMenuClick('Resolve Data Quality Issues')}
                                className="bg-red-500 hover:bg-red-600 text-white font-bold py-3 px-6 rounded-lg shadow-lg transition duration-300 ease-in-out transform hover:scale-105"
                            >
                                Resolve Data Quality Issues
                            </button>
                            <button
                                onClick={() => handleMainMenuClick('View Quality Dashboard')}
                                className="bg-purple-500 hover:bg-purple-600 text-white font-bold py-3 px-6 rounded-lg shadow-lg transition duration-300 ease-in-out transform hover:scale-105"
                            >
                                View Quality Dashboard
                            </button>
                        </div>
                        {userId && (
                            <p className="text-sm text-gray-500 mt-6">
                                Your User ID: <span className="font-mono bg-gray-100 p-1 rounded">{userId}</span>
                            </p>
                        )}
                    </div>
                );
        }
    };

    return (
        <div className="min-h-screen bg-gray-100 p-4 sm:p-8 flex items-start justify-center font-sans">
            <style>{`
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
                body {
                    font-family: 'Inter', sans-serif;
                }
                @keyframes fade-in-up {
                    from {
                        opacity: 0;
                        transform: translateY(20px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
                .animate-fade-in-up {
                    animation: fade-in-up 0.3s ease-out forwards;
                }
            `}</style>
            <div className="w-full max-w-4xl bg-gradient-to-br from-white to-gray-50 p-6 rounded-xl shadow-2xl border border-gray-200">
                <h1 className="text-4xl font-bold text-center text-indigo-800 mb-8 pb-4 border-b-2 border-indigo-200">
                    Data Quality Assistant
                </h1>

                {renderContent()}

                {userTaskChoice && userTaskChoice !== 'Exit' && (
                    <div className="mt-10 pt-6 border-t-2 border-gray-200 text-center">
                        <p className="text-gray-700 mb-4">Would you like to return to the main menu or perform another task?</p>
                        <div className="flex flex-wrap justify-center gap-4">
                            <button
                                onClick={() => handleMainMenuClick('Go to Home')}
                                className="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-5 rounded-lg shadow-sm transition duration-300 ease-in-out transform hover:scale-105"
                            >
                                Go to Home
                            </button>
                            <button
                                onClick={() => handleMainMenuClick('Exit')}
                                className="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-5 rounded-lg shadow-sm transition duration-300 ease-in-out transform hover:scale-105"
                            >
                                Exit
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {showModal && (
                <Modal
                    title={modalTitle}
                    message={modalMessage}
                    onClose={() => setShowModal(false)}
                />
            )}
        </div>
    );
};

export default App;
