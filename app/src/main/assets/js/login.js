document.addEventListener("DOMContentLoaded", function () {

    const phoneStep =
        document.getElementById("phoneStep");

    const otpStep =
        document.getElementById("otpStep");

    const contactStep =
        document.getElementById("contactStep");

    const phoneNumber =
        document.getElementById("phoneNumber");

    const otpNumber =
        document.getElementById("otpNumber");

    let userPhoneNumber = "";


    function keepOnlyNumbers(input, maximumLength) {
        input.value = input.value
            .replace(/\D/g, "")
            .slice(0, maximumLength);
    }


    phoneNumber.addEventListener("input", function () {
        keepOnlyNumbers(phoneNumber, 10);

        document.getElementById("phoneError").textContent = "";
    });


    otpNumber.addEventListener("input", function () {
        keepOnlyNumbers(otpNumber, 6);

        document.getElementById("otpError").textContent = "";
    });


    function showStep(stepName) {

        phoneStep.classList.remove("active-step");
        otpStep.classList.remove("active-step");
        contactStep.classList.remove("active-step");

        phoneStep.setAttribute("aria-hidden", "true");
        otpStep.setAttribute("aria-hidden", "true");
        contactStep.setAttribute("aria-hidden", "true");


        if (stepName === "phone") {
            phoneStep.classList.add("active-step");
            phoneStep.setAttribute("aria-hidden", "false");
        }


        if (stepName === "otp") {
            otpStep.classList.add("active-step");
            otpStep.setAttribute("aria-hidden", "false");
        }


        if (stepName === "contact") {
            contactStep.classList.add("active-step");
            contactStep.setAttribute("aria-hidden", "false");
        }


        window.scrollTo(0, 0);
    }


    // Send OTP

    document
        .getElementById("phoneForm")
        .addEventListener("submit", function (event) {

            event.preventDefault();


            const phone =
                phoneNumber.value.trim();

            const phoneError =
                document.getElementById("phoneError");

            const phoneStatus =
                document.getElementById("phoneStatus");


            phoneError.textContent = "";
            phoneStatus.textContent = "";


            if (!/^[6-9]\d{9}$/.test(phone)) {

                phoneError.textContent =
                    "Enter a valid 10-digit Indian mobile number.";

                return;
            }


            userPhoneNumber = phone;

            phoneStatus.textContent =
                "Sending OTP…";


            if (
                window.KavachAndroid &&
                typeof window.KavachAndroid.sendOtp === "function"
            ) {
                window.KavachAndroid.sendOtp("+91" + phone);
            } else {
                phoneStatus.textContent =
                    "Android authentication is not connected.";
            }

        });


    // Verify OTP

    document
        .getElementById("otpForm")
        .addEventListener("submit", function (event) {

            event.preventDefault();


            const otp =
                otpNumber.value.trim();

            const otpError =
                document.getElementById("otpError");

            const otpStatus =
                document.getElementById("otpStatus");


            otpError.textContent = "";
            otpStatus.textContent = "";


            if (!/^\d{6}$/.test(otp)) {

                otpError.textContent =
                    "Enter the complete 6-digit OTP.";

                return;
            }


            otpStatus.textContent =
                "Verifying OTP…";


            if (
                window.KavachAndroid &&
                typeof window.KavachAndroid.verifyOtp === "function"
            ) {
                window.KavachAndroid.verifyOtp(otp);
            } else {
                otpStatus.textContent =
                    "Android authentication is not connected.";
            }

        });


    // Change phone number

    document
        .getElementById("changeNumberButton")
        .addEventListener("click", function () {

            otpNumber.value = "";

            showStep("phone");

        });


    /*
     * Kotlin calls this after Firebase sends the OTP.
     */

    window.onOtpSent = function () {

        document.getElementById("phoneStatus").textContent = "";

        document.getElementById("otpPhoneDisplay").textContent =
            "+91 ••••••" + userPhoneNumber.slice(-4);

        showStep("otp");

        otpNumber.focus();
    };


    /*
     * Kotlin calls this after Firebase verifies the OTP.
     */

    window.onOtpVerified = function () {

        document.getElementById("otpStatus").textContent =
            "Mobile number verified successfully.";

        setTimeout(function () {
            showStep("contact");
        }, 600);
    };


    /*
     * Kotlin calls this if sending or verifying OTP fails.
     */

    window.onAuthenticationError = function (message) {

        const phoneStepVisible =
            phoneStep.classList.contains("active-step");


        if (phoneStepVisible) {

            document.getElementById("phoneStatus").textContent =
                message;

        } else {

            document.getElementById("otpStatus").textContent =
                message;

        }
    };

});