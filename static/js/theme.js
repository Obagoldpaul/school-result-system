(function () {
    const STORAGE_KEY = "paulschoolhub-theme";

    function applyTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem(STORAGE_KEY, theme);

        const button = document.getElementById("theme-toggle");

        if (button) {
            if (theme === "dark") {
                button.textContent = "☀ Light";
                button.setAttribute("aria-label", "Switch to light mode");
                button.setAttribute("title", "Switch to light mode");
            } else {
                button.textContent = "🌙 Dark";
                button.setAttribute("aria-label", "Switch to dark mode");
                button.setAttribute("title", "Switch to dark mode");
            }
        }
    }

    const savedTheme = localStorage.getItem(STORAGE_KEY);
    const initialTheme = savedTheme === "dark" ? "dark" : "light";

    document.documentElement.setAttribute("data-theme", initialTheme);

    document.addEventListener("DOMContentLoaded", function () {
        const button = document.getElementById("theme-toggle");

        if (!button) {
            return;
        }

        applyTheme(initialTheme);

        button.addEventListener("click", function () {
            const currentTheme =
                document.documentElement.getAttribute("data-theme");

            applyTheme(currentTheme === "dark" ? "light" : "dark");
        });
    });
})();