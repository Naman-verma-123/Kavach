package com.dsafiles.kavach

import android.annotation.SuppressLint
import android.os.Bundle
import android.webkit.JavascriptInterface
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.appcompat.app.AppCompatActivity
import com.google.firebase.FirebaseException
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseAuthInvalidCredentialsException
import com.google.firebase.auth.PhoneAuthCredential
import com.google.firebase.auth.PhoneAuthOptions
import com.google.firebase.auth.PhoneAuthProvider
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var firebaseAuth: FirebaseAuth

    private var verificationId: String? = null


    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContentView(R.layout.activity_main)

        firebaseAuth = FirebaseAuth.getInstance()

        webView = findViewById(R.id.webView)

        webView.webViewClient = WebViewClient()

        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = true
        }


        // Register JavaScript-to-Kotlin bridge.

        webView.addJavascriptInterface(
            WebAppInterface(),
            "KavachAndroid"
        )


        // Login is the first page during setup.

        webView.loadUrl(
            "file:///android_asset/login.html"
        )
    }


    /*
     * Functions available to login.js as:
     *
     * KavachAndroid.sendOtp(...)
     * KavachAndroid.verifyOtp(...)
     */

    inner class WebAppInterface {

        @JavascriptInterface
        fun sendOtp(phoneNumber: String) {

            runOnUiThread {
                sendFirebaseOtp(phoneNumber)
            }
        }


        @JavascriptInterface
        fun verifyOtp(otp: String) {

            runOnUiThread {
                verifyFirebaseOtp(otp)
            }
        }
    }


    /*
     * Request OTP from Firebase.
     */

    private fun sendFirebaseOtp(phoneNumber: String) {

        val callbacks =
            object : PhoneAuthProvider.OnVerificationStateChangedCallbacks() {


                /*
                 * Android may automatically verify the number
                 * without requiring manual OTP entry.
                 */

                override fun onVerificationCompleted(
                    credential: PhoneAuthCredential
                ) {
                    signInWithCredential(credential)
                }


                /*
                 * Called when Firebase cannot send or verify OTP.
                 */

                override fun onVerificationFailed(
                    exception: FirebaseException
                ) {

                    showAuthenticationError(
                        exception.localizedMessage
                            ?: "Unable to send OTP. Please try again."
                    )
                }


                /*
                 * Called after Firebase accepts the request
                 * and sends/configures the OTP.
                 */

                override fun onCodeSent(
                    newVerificationId: String,
                    token: PhoneAuthProvider.ForceResendingToken
                ) {
                    super.onCodeSent(
                        newVerificationId,
                        token
                    )

                    verificationId = newVerificationId

                    callJavaScript(
                        "window.onOtpSent()"
                    )
                }
            }


        val options =
            PhoneAuthOptions
                .newBuilder(firebaseAuth)
                .setPhoneNumber(phoneNumber)
                .setTimeout(
                    60L,
                    TimeUnit.SECONDS
                )
                .setActivity(this)
                .setCallbacks(callbacks)
                .build()


        PhoneAuthProvider.verifyPhoneNumber(options)
    }


    /*
     * Create a Firebase credential from the OTP.
     */

    private fun verifyFirebaseOtp(otp: String) {

        val savedVerificationId = verificationId


        if (savedVerificationId == null) {

            showAuthenticationError(
                "Please request a new OTP first."
            )

            return
        }


        val credential =
            PhoneAuthProvider.getCredential(
                savedVerificationId,
                otp
            )


        signInWithCredential(credential)
    }


    /*
     * Complete Firebase Authentication.
     */

    private fun signInWithCredential(
        credential: PhoneAuthCredential
    ) {

        firebaseAuth
            .signInWithCredential(credential)
            .addOnCompleteListener(this) { task ->


                if (task.isSuccessful) {

                    callJavaScript(
                        "window.onOtpVerified()"
                    )

                } else {

                    val message =
                        if (
                            task.exception
                                    is FirebaseAuthInvalidCredentialsException
                        ) {
                            "The OTP is incorrect. Please try again."
                        } else {
                            task.exception?.localizedMessage
                                ?: "OTP verification failed."
                        }


                    showAuthenticationError(message)
                }
            }
    }


    /*
     * Run a JavaScript function inside the WebView.
     */

    private fun callJavaScript(
        javascript: String
    ) {

        runOnUiThread {

            webView.evaluateJavascript(
                javascript,
                null
            )
        }
    }


    /*
     * Safely send an error message from Kotlin to JavaScript.
     */

    private fun showAuthenticationError(
        message: String
    ) {

        val safeMessage =
            JSONObject.quote(message)


        callJavaScript(
            "window.onAuthenticationError($safeMessage)"
        )
    }
}