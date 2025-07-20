function initFormValidation(config) {
    const fields = config.fields;

    Object.keys(fields).forEach(key => {
        const field = fields[key];
        const input = document.querySelector(field.selector);
        if (!input) return;

        const errorElement = document.createElement("div");
        errorElement.classList.add("validation-error");
        errorElement.style.color = "red";
        errorElement.style.fontSize = "0.9em";
        errorElement.style.marginTop = "4px";
        input.parentNode.appendChild(errorElement);

        const validate = () => {
            const value = input.value.trim();
            let error = "";

            if (field.rules.required && value === "") {
                error = "Trường này không được để trống.";
            } else if (field.rules.minLength && value.length < field.rules.minLength) {
                error = `Tối thiểu ${field.rules.minLength} ký tự.`;
            } else if (field.rules.maxLength && value.length > field.rules.maxLength) {
                error = `Tối đa ${field.rules.maxLength} ký tự.`;
            } else if (field.rules.noEmoji && /[\uD800-\uDFFF]/.test(value)) {
                error = "Không được chứa emoji.";
            } else if (field.rules.noSpecialChars && /[^a-zA-Z0-9\sÀ-ỹ]/.test(value)) {
                error = "Không được chứa ký tự đặc biệt.";
            }

            if (error) {
                errorElement.textContent = field.errorMessage || error;
                input.classList.add("is-invalid");
                return false;
            } else {
                errorElement.textContent = "";
                input.classList.remove("is-invalid");
                return true;
            }
        };

        input.addEventListener("input", validate);
        input.form.addEventListener("submit", function (e) {
            const isValid = validate();
            if (!isValid) e.preventDefault();
        });
    });
}
