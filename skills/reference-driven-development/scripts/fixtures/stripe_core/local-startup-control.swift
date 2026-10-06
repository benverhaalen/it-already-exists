import Foundation
import Flutter
import Darwin
@_spi(STP) import StripeCore

// This guards only this API client's transport, not the whole native process.
private final class RDDUnavailablePaymentTransport: URLProtocol {
  override class func canInit(with request: URLRequest) -> Bool { true }
  override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
  override func startLoading() {
    NSLog("RDD_STRIPE_TRANSPORT_UNAVAILABLE localTestAuthority=1")
    client?.urlProtocol(self, didFailWithError: NSError(domain:NSURLErrorDomain,code:NSURLErrorNotConnectedToInternet))
  }
  override func stopLoading() {}
}

@objc public final class RDDStripeHost: NSObject {
  private static var live: RDDStripeHost?
  private var configured = false
  private var urlScheme: String?
  private var merchantIdentifier: String?
  private let apiClient: STPAPIClient
  private override init() {
    // Native API-client construction itself otherwise sends fraud telemetry.
    StripeAPI.advancedFraudSignalsEnabled = false
    setenv("UITesting", "1", 1)
    apiClient = STPAPIClient.shared
    let config = URLSessionConfiguration.ephemeral
    config.protocolClasses = [RDDUnavailablePaymentTransport.self]
    apiClient.urlSession = URLSession(configuration: config)
    apiClient.apiURL = URL(string:"http://127.0.0.1:8084/v1")!
    super.init()
  }
  private func initialise(_ params: [String: Any]) -> FlutterError? {
    guard let key = params["publishableKey"] as? String, key.hasPrefix("pk_test_"),
          let appInfo = params["appInfo"] as? [String:Any] else {
      return FlutterError(code:"local-test-configuration-required",message:"A local test publishable key and appInfo are required",details:nil)
    }
    if let parameters = params["threeDSecureParams"], !(parameters is NSNull) {
      return FlutterError(code:"unsupported-local-contract",message:"3DS configuration has not been qualified",details:nil)
    }
    apiClient.publishableKey = key
    StripeAPI.defaultPublishableKey = key
    apiClient.stripeAccount = params["stripeAccountId"] as? String
    apiClient.appInfo = STPAppInfo(name:appInfo["name"] as? String ?? "",partnerId:appInfo["partnerId"] as? String ?? "",version:appInfo["version"] as? String ?? "",url:appInfo["url"] as? String ?? "")
    urlScheme = params["urlScheme"] as? String
    merchantIdentifier = params["merchantIdentifier"] as? String
    configured = true
    NSLog("RDD_STRIPE_INITIALIZED nativeCore=1 localTestAuthority=1 purchaseTransport=unavailable")
    return nil
  }
  @objc public static func registerMessenger(_ messenger: FlutterBinaryMessenger) {
    let host = RDDStripeHost(); live = host
    let probe:[String:Any] = ["publishableKey":"pk_test_rdd_inert_no_payment_authority","appInfo":["name":"RDDControl","version":"1"],"threeDSecureParams":NSNull()]
    let pass = host.initialise(probe) == nil && host.configured && !StripeAPI.advancedFraudSignalsEnabled && !STPTelemetryClient.shouldSendTelemetry() && !STPAnalyticsClient.sharedClient.shouldSendAnalytic() && host.apiClient.publishableKey == probe["publishableKey"] as? String && host.apiClient.apiURL.host == "127.0.0.1"
    precondition(pass,"Native Stripe configuration control failed")
    host.configured = false
    NSLog("RDD_STRIPE_CONFIGURATION_CONTROL_PASS telemetryDisabled=1 analyticsDisabled=1 nativeState=1")
    let group = DispatchGroup(), lock = NSLock()
    var rejected = 0
    for url in ["https://example.invalid/rdd-control", "http://127.0.0.1:8084/v1/rdd-control"] {
      group.enter()
      host.apiClient.urlSession.dataTask(with:URL(string:url)!) { data,response,error in
        lock.lock()
        if data == nil && response == nil && (error as NSError?)?.code == NSURLErrorNotConnectedToInternet { rejected += 1 }
        lock.unlock();group.leave()
      }.resume()
    }
    let finished = group.wait(timeout:.now()+5) == .success
    lock.lock();let allRejected = rejected == 2;lock.unlock()
    precondition(finished && allRejected,"Native Stripe transport rejection control failed")
    NSLog("RDD_STRIPE_TRANSPORT_CONTROL_PASS externalRejected=1 localUnavailable=1")
    let channel = FlutterMethodChannel(name:"flutter.stripe/payments",binaryMessenger:messenger,codec:FlutterJSONMethodCodec())
    channel.setMethodCallHandler { call, result in
      NSLog("RDD_STRIPE_CALL %@",call.method)
      guard call.method == "initialise" else {
        result(FlutterError(code:"unsupported-local-contract",message:"This payment operation needs a qualified local test adapter",details:nil)); return
      }
      guard let params = call.arguments as? [String:Any] else {
        result(FlutterError(code:"invalid-arguments",message:"Expected a configuration object",details:nil));return
      }
      result(host.initialise(params))
    }
  }
}
