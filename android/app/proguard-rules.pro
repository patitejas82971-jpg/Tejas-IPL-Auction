# ProGuard rules for IPL Auction Android App

# Keep JavaScript Interface methods so WebView bridge works in release mode
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}

-keep class com.iplauction.app.WebAppInterface {
    public <methods>;
}

# AndroidX WebKit
-keep class androidx.webkit.** { *; }
