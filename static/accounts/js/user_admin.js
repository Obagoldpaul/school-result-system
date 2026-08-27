console.log("PAUL SCHOOLHUB USER ADMIN JS LOADED");
document.addEventListener("DOMContentLoaded", function () {

    const schoolField = document.getElementById("id_school");
    const roleField = document.getElementById("id_school_role");

    if (!schoolField || !roleField) {
        return;
    }

    function loadSchoolRoles(schoolId, selectedRoleId = null) {

        // Clear current options.
        roleField.innerHTML = "";

        // Add empty option.
        const emptyOption = document.createElement("option");
        emptyOption.value = "";
        emptyOption.textContent = "---------";

        roleField.appendChild(emptyOption);

        if (!schoolId) {
            return;
        }

        const url =
            `/admin/accounts/user/school-roles/${schoolId}/`;

        fetch(url)
            .then(response => {

                if (!response.ok) {
                    throw new Error(
                        "Unable to load school roles."
                    );
                }

                return response.json();
            })

            .then(data => {

                data.roles.forEach(role => {

                    const option =
                        document.createElement("option");

                    option.value = role.id;
                    option.textContent = role.name;

                    if (
                        selectedRoleId &&
                        String(role.id) === String(selectedRoleId)
                    ) {
                        option.selected = true;
                    }

                    roleField.appendChild(option);
                });

            })

            .catch(error => {

                console.error(
                    "School role loading error:",
                    error
                );

            });
    }


    // ---------------------------------------------------------
    // WHEN SCHOOL CHANGES
    // ---------------------------------------------------------

    schoolField.addEventListener("change", function () {

        loadSchoolRoles(
            this.value
        );

    });


    // ---------------------------------------------------------
    // WHEN PAGE FIRST LOADS
    // ---------------------------------------------------------

    if (schoolField.value) {

        const currentRole =
            roleField.value;

        loadSchoolRoles(
            schoolField.value,
            currentRole
        );
    }

});
