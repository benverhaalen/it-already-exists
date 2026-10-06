import UIKit
import FirebaseCore
import FirebaseFunctions

@main final class AppDelegate: UIResponder, UIApplicationDelegate {
  var window: UIWindow?
  func application(_ application: UIApplication, didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey:Any]?) -> Bool {
    precondition(ProcessInfo.processInfo.environment["RDD_FUNCTIONS_LOCAL_ONLY"] == "1")
    let config=FirebaseOptions(googleAppID:"1:123456789:ios:0123456789abcdef",gcmSenderID:"123456789")
    config.apiKey="rdd-local-inert-key";config.projectID="demo-rdd-accounts"
    FirebaseApp.configure(options:config)
    FirebaseApp.app()!.isDataCollectionDefaultEnabled=false
    let functions=Functions.functions(region:"us-central1")
    functions.useEmulator(withHost:"127.0.0.1",port:5006)
    window=UIWindow(frame:UIScreen.main.bounds)
    let view=UIViewController();view.view.backgroundColor = .systemBackground
    let label=UILabel(frame:CGRect(x:20,y:100,width:350,height:200));label.numberOfLines=0
    label.text="Real native callable transport control";view.view.addSubview(label)
    window?.rootViewController=view;window?.makeKeyAndVisible()
    Task { @MainActor in
      do {
        let guardCases = try rddRunCallableGuardControl()
        let payload:[String:Any]=["integer":Int64(9007199254740993),"bool":true,"null":NSNull(),"list":["a","b"]]
        let result=try await functions.httpsCallable("rddEcho").call(payload)
        guard let data=result.data as? [String:Any], let number=data["integer"] as? NSNumber,
              number.int64Value == 9007199254740993,
              data["bool"] as? Bool == true, data["null"] is NSNull,
              data["list"] as? [String] == ["a","b"] else { throw NSError(domain:"RDDCallableControl",code:1) }
        var denied=false
        do { _ = try await functions.httpsCallable("rddDenied").call() }
        catch {
          let error=error as NSError
          denied=error.domain == "com.firebase.functions" && error.code == FunctionsErrorCode.permissionDenied.rawValue
        }
        guard denied else { throw NSError(domain:"RDDCallableControl",code:2) }
        var malformed=false
        do { _ = try await functions.httpsCallable("rddMalformed").call() }
        catch {
          let error=error as NSError
          malformed=error.domain == "com.firebase.functions" && error.code == FunctionsErrorCode.internal.rawValue
        }
        guard malformed else { throw NSError(domain:"RDDCallableControl",code:3) }
        // These addresses are not requested: the opt-in SDK guard rejects before token acquisition.
        for endpoint in ["https://example.invalid/rddEcho","http://127.0.0.1:5006/not-demo/us-central1/rddEcho",
                         "http://127.0.0.1:5006/demo-rdd-accounts/us-central1/rddEcho?override=1"] {
          var rejected=false
          do { _ = try await functions.httpsCallable(URL(string:endpoint)!).call() }
          catch { rejected=(error as NSError).domain == "RDDLocalFunctionsTransport" }
          guard rejected else { throw NSError(domain:"RDDCallableControl",code:4) }
        }
        label.text="PASS: native echo, integer/null/list preservation, callable error, malformed response and endpoint rejection"
        NSLog("RDD_FUNCTIONS_NATIVE_CONTROL_PASS echo=1 int64=1 null=1 list=1 error200=1 malformed=1 deniedEndpoints=3 guardCases=%ld", guardCases)
      } catch {
        let error=error as NSError
        label.text="FAIL: inspect scoped native control log"
        NSLog("RDD_FUNCTIONS_NATIVE_CONTROL_FAIL domain=%@ code=%ld",error.domain,error.code)
      }
    }
    return true
  }
}
