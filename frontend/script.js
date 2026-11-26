
// =====================================
// MSRIT EXAM FLOW - FRONTEND CONTROLLER
// =====================================


// =====================================
// 1. DATABASE AND BACKEND CONFIGURATION
// =====================================

const API_BASE = "http://127.0.0.1:8000";

const database = {
    students: [],
    exams: [],
    rooms: [],
    invigilators: []
};

// Stores the complete backend dataset,
// including slots and constraints.
let fullDataset = null;


// =====================================
// 2. PAGE NAVIGATION
// =====================================

const pageInfo = {
    overview: [
        "Overview",
        "Welcome to your examination command centre."
    ],

    datahub: [
        "Data Hub",
        "Manage examination-related information."
    ],

    constraints: [
        "Constraints",
        "Configure scheduling rules and restrictions."
    ],

    generator: [
        "Schedule Generator",
        "Generate an optimised examination timetable."
    ],

    timetable: [
        "Timetable",
        "View your generated examination schedule."
    ],

    conflicts: [
        "Conflict Centre",
        "Identify scheduling conflicts and violations."
    ],

    reports: [
        "Reports",
        "Review scheduling performance and statistics."
    ]
};


function navigateTo(pageId) {

    document.querySelectorAll(".page-section").forEach(section => {
        section.classList.remove("active");
    });

    document.querySelectorAll(".nav-link").forEach(link => {
        link.classList.remove("active");
    });

    const selectedPage = document.getElementById(pageId);

    if (!selectedPage) return;

    selectedPage.classList.add("active");

    const selectedLink = document.querySelector(
        `.nav-link[data-page="${pageId}"]`
    );

    if (selectedLink) {
        selectedLink.classList.add("active");
    }

    document.getElementById("pageTitle").textContent =
        pageInfo[pageId][0];

    document.getElementById("pageSubtitle").textContent =
        pageInfo[pageId][1];
}


document.querySelectorAll(".nav-link").forEach(link => {

    link.addEventListener("click", event => {

        event.preventDefault();

        navigateTo(link.dataset.page);

    });

});


// =====================================
// 3. BACKEND CONNECTION
// =====================================

async function loadDataset() {

    try {

        console.log("Connecting to MSRITExamFlow backend...");

        const response = await fetch(
            `${API_BASE}/api/dataset`
        );

        if (!response.ok) {
            throw new Error("Could not retrieve backend dataset.");
        }

        const data = await response.json();

        // Preserve the complete dataset.
        fullDataset = data;

        // Load the four Data Hub categories.
        database.students = data.students;
        database.exams = data.exams;
        database.rooms = data.rooms;
        database.invigilators = data.invigilators;

        console.log("Backend connected successfully!");

        console.log("Students:", database.students);
        console.log("Exams:", database.exams);
        console.log("Rooms:", database.rooms);
        console.log("Invigilators:", database.invigilators);

        updateStatistics();

        renderDataTable();

    } catch (error) {

        console.error("Backend connection failed:", error);

        alert(
            "Could not connect to the backend. " +
            "Make sure FastAPI is running at http://127.0.0.1:8000"
        );

    }

}


// =====================================
// 4. SAVE DATASET TO BACKEND
// =====================================

async function saveDatasetToBackend() {

    if (!fullDataset) {
        throw new Error("Backend dataset has not loaded yet.");
    }

    const updatedDataset = {
        ...fullDataset,

        students: database.students,
        exams: database.exams,
        rooms: database.rooms,
        invigilators: database.invigilators
    };

    const response = await fetch(
        `${API_BASE}/api/dataset`,
        {
            method: "PUT",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify(updatedDataset)
        }
    );

    const result = await response.json();

    if (!response.ok) {

        throw new Error(
            result.detail || "Could not save dataset."
        );

    }

    fullDataset = updatedDataset;

    console.log("Dataset saved successfully!");

    return result;

}


// =====================================
// 5. DATA HUB CONFIGURATION
// =====================================

const categoryInfo = {

    students: {

        title: "Student Management",

        description: "Manage registered students.",

        fields: [
            { key: "id", label: "Student ID", type: "text" },
            { key: "name", label: "Name", type: "text" },
            { key: "exam_ids", label: "Exam IDs", type: "array" }
        ]

    },

    exams: {

        title: "Examination Management",

        description: "Manage examination subjects.",

        fields: [
            { key: "id", label: "Exam ID", type: "text" },
            { key: "name", label: "Exam Name", type: "text" },
            { key: "duration_minutes", label: "Duration (minutes)", type: "number" },
            { key: "required_invigilators_per_room", label: "Invigilators per room", type: "number" },
            { key: "eligible_slot_ids", label: "Eligible Slot IDs", type: "array" }
        ]

    },

    rooms: {

        title: "Room Management",

        description: "Manage examination rooms and capacities.",

        fields: [
            { key: "id", label: "Room ID", type: "text" },
            { key: "name", label: "Room Name", type: "text" },
            { key: "building", label: "Building", type: "text" },
            { key: "capacity", label: "Capacity", type: "number" },
            { key: "available_slot_ids", label: "Available Slot IDs", type: "array" }
        ]

    },

    invigilators: {

        title: "Invigilator Management",

        description: "Manage available invigilation staff.",

        fields: [
            { key: "id", label: "Staff ID", type: "text" },
            { key: "name", label: "Name", type: "text" },
            { key: "available_slot_ids", label: "Available Slot IDs", type: "array" },
            { key: "max_assignments", label: "Maximum Assignments", type: "number" }
        ]

    }

};


let currentCategory = "students";


// =====================================
// 6. HTML ESCAPING
// =====================================

function escapeHTML(value) {

    const element = document.createElement("span");

    element.textContent = String(value ?? "");

    return element.innerHTML;

}


// =====================================
// 7. DISPLAY DATA HUB TABLE
// =====================================

function renderDataTable() {

    const info = categoryInfo[currentCategory];

    const records = database[currentCategory];

    if (!info || !Array.isArray(records)) return;

    document.getElementById("dataHeading").textContent =
        info.title;

    document.getElementById("dataDescription").textContent =
        info.description;


    // Generate table headings.

    document.getElementById("dataTableHead").innerHTML = `
        <tr>
            ${info.fields.map(field =>
        `<th>${escapeHTML(field.label)}</th>`
    ).join("")}

            <th>Action</th>
        </tr>
    `;


    // Generate table rows.

    document.getElementById("dataTableBody").innerHTML =

        records.map((record, index) => `

            <tr>

                ${info.fields.map(field => {

            let value = record[field.key];

            if (Array.isArray(value)) {
                value = value.join(", ");
            }

            return `
                        <td>${escapeHTML(value)}</td>
                    `;

        }).join("")}

                <td>

                    <button
                        class="delete-btn"
                        data-index="${index}"
                    >
                        Delete
                    </button>

                </td>

            </tr>

        `).join("");


    document.getElementById("dataEmptyMessage").style.display =
        records.length ? "none" : "block";


    updateStatistics();

}


// =====================================
// 8. SWITCH DATA HUB CATEGORIES
// =====================================

document.querySelectorAll(".data-category").forEach(button => {

    button.addEventListener("click", () => {

        currentCategory = button.dataset.category;

        renderDataTable();

    });

});


// =====================================
// 9. ADD NEW RECORD
// =====================================

document.getElementById("addRecordBtn").addEventListener(
    "click",
    async () => {

        if (!fullDataset) {

            alert("Please wait for the backend data to load.");

            return;

        }

        const info = categoryInfo[currentCategory];

        const record = {};

        // Collect all fields.

        for (const field of info.fields) {

            let value = prompt(
                `Enter ${field.label}:`
            );

            if (value === null) return;

            value = value.trim();

            if (!value) {

                alert("Please fill in every field.");

                return;

            }

            // Convert comma-separated values into arrays.

            if (field.type === "array") {

                const values = value
                    .split(",")
                    .map(item => item.trim())
                    .filter(item => item.length > 0);

                if (values.length === 0) {

                    alert(`Enter at least one value for ${field.label}.`);

                    return;

                }

                record[field.key] = values;

            }

            // Convert numeric fields.

            else if (field.type === "number") {

                const numberValue = Number(value);

                if (
                    !Number.isInteger(numberValue) ||
                    numberValue < 0
                ) {

                    alert(`Enter a valid whole number for ${field.label}.`);

                    return;

                }

                if (
                    (field.key === "duration_minutes" ||
                        field.key === "capacity") &&
                    numberValue === 0
                ) {

                    alert(`${field.label} must be greater than zero.`);

                    return;

                }

                record[field.key] = numberValue;

            }

            else {

                record[field.key] = value;

            }

        }


        // Save the new record.

        database[currentCategory].push(record);

        try {

            await saveDatasetToBackend();

            alert("Record added and saved successfully!");

            renderDataTable();

        } catch (error) {

            // Undo the local change if saving fails.

            database[currentCategory].pop();

            console.error(error);

            alert("Could not save record: " + error.message);

            renderDataTable();

        }

    }
);


// =====================================
// 10. DELETE RECORD
// =====================================

document.getElementById("dataTableBody").addEventListener(
    "click",
    async event => {

        if (!event.target.classList.contains("delete-btn")) {
            return;
        }

        const index = Number(event.target.dataset.index);

        if (!confirm("Are you sure you want to delete this record?")) {
            return;
        }

        // Keep a copy in case saving fails.

        const removedRecord = database[currentCategory][index];

        database[currentCategory].splice(index, 1);

        try {

            await saveDatasetToBackend();

            alert("Record deleted successfully!");

            renderDataTable();

        } catch (error) {

            // Restore the record if the backend rejects the change.

            database[currentCategory].splice(
                index,
                0,
                removedRecord
            );

            console.error(error);

            alert("Could not delete record: " + error.message);

            renderDataTable();

        }

    }
);


// =====================================
// 11. UPDATE DASHBOARD STATISTICS
// =====================================

function updateStatistics() {

    const studentCount = document.getElementById("studentCount");
    const examCount = document.getElementById("examCount");
    const roomCount = document.getElementById("roomCount");
    const invigilatorCount = document.getElementById("invigilatorCount");

    if (studentCount) {
        studentCount.textContent = database.students.length;
    }

    if (examCount) {
        examCount.textContent = database.exams.length;
    }

    if (roomCount) {
        roomCount.textContent = database.rooms.length;
    }

    if (invigilatorCount) {
        invigilatorCount.textContent = database.invigilators.length;
    }


    // Update report statistics if these elements exist.

    const reportExamCount = document.getElementById("reportExamCount");

    const reportRoomCount = document.getElementById("reportRoomCount");

    if (reportExamCount) {
        reportExamCount.textContent = database.exams.length;
    }

    if (reportRoomCount) {
        reportRoomCount.textContent = database.rooms.length;
    }

}


// =====================================
// 12. CONSTRAINTS
// =====================================

document.getElementById("saveConstraintsBtn").addEventListener(
    "click",
    () => {

        const constraints = {

            examGap: Number(
                document.getElementById("examGap").value
            ),

            roomUtilisation: Number(
                document.getElementById("roomUtilisation").value
            ),

            examDuration: Number(
                document.getElementById("examDuration").value
            ),

            maxInvigilation: Number(
                document.getElementById("maxInvigilation").value
            )

        };


        if (

            Object.values(constraints).some(
                value => !Number.isFinite(value) || value < 0
            )

            ||

            constraints.roomUtilisation < 1

            ||

            constraints.roomUtilisation > 100

            ||

            constraints.examDuration < 1

            ||

            constraints.maxInvigilation < 1

        ) {

            alert("Please enter valid constraint values.");

            return;

        }


        localStorage.setItem(
            "examFlowConstraints",
            JSON.stringify(constraints)
        );


        document.getElementById("constraintMessage").textContent =
            "Constraints saved successfully in this browser.";

    }
);


// =====================================
// 13. SCHEDULE GENERATOR - FASTAPI
// =====================================

document.getElementById("runSolverBtn").addEventListener(
    "click",
    async () => {

        const message = document.getElementById("generationMessage");

        const button = document.getElementById("runSolverBtn");

        message.textContent = "Generating timetable... Please wait.";

        button.disabled = true;


        try {

            const response = await fetch(
                `${API_BASE}/api/generate-timetable`,
                {
                    method: "POST"
                }
            );


            const result = await response.json();


            if (!response.ok) {

                throw new Error(
                    result.detail || "Timetable generation failed."
                );

            }


            if (result.status !== "success") {

                throw new Error(
                    result.message || "No feasible timetable found."
                );

            }


            displayTimetable(result.timetable, result.summary);



            message.textContent =
                `Timetable generated successfully! Solver: ${result.solver_status || "Completed"}`;

            navigateTo("timetable");


            console.log("Generated timetable:", result);

        }

        catch (error) {

            console.error("Timetable generation error:", error);

            message.textContent =
                "Error: " + error.message;

        }

        finally {

            button.disabled = false;

        }

    }
);


// =====================================
// 14. TIMETABLE DISPLAY
// =====================================


// =====================================
// 14. TIMETABLE DISPLAY
// =====================================

function displayTimetable(timetable, summary) {

    const tbody = document.getElementById("timetableBody");

    if (!timetable || timetable.length === 0) {

        tbody.innerHTML = `
            <tr>
                <td colspan="8">No timetable records returned.</td>
            </tr>
        `;

        return;

    }

    tbody.innerHTML = timetable.map(item => `

        <tr>

            <td>${escapeHTML(item.exam_name)}</td>

            <td>${escapeHTML(item.date)}</td>

            <td>
                ${escapeHTML(
                    item.start_time + " - " + item.end_time
                )}
            </td>

            <td>${escapeHTML(item.room_name)}</td>

            <td>${escapeHTML(item.student_count ?? 0)}</td>

            <td>${escapeHTML(item.room_capacity ?? 0)}</td>

            <td>
                ${escapeHTML(item.room_utilization_percent ?? 0)}%
            </td>

            <td>
                ${escapeHTML(
                    (item.invigilator_ids || []).join(", ")
                )}
            </td>

        </tr>

    `).join("");

    console.log("Timetable summary:", summary);

}



// =====================================
// 15. REPORT EXPORT
// =====================================

document.getElementById("exportReportBtn").addEventListener(
    "click",
    () => {

        const report = {

            project: "MSRITExamFlow",

            students: database.students.length,

            examinations: database.exams.length,

            rooms: database.rooms.length,

            invigilators: database.invigilators.length,

            generatedAt: new Date().toLocaleString()

        };


        const blob = new Blob(
            [JSON.stringify(report, null, 2)],
            {
                type: "application/json"
            }
        );


        const url = URL.createObjectURL(blob);

        const link = document.createElement("a");

        link.href = url;

        link.download = "MSRITExamFlow-Report.json";

        link.click();

        URL.revokeObjectURL(url);

    }
);


// =====================================
// 16. START APPLICATION
// =====================================

// Load the backend dataset only after all
// frontend functions and event listeners exist.

loadDataset();

