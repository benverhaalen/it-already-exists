import Foundation
import DatadogCore
import DatadogInternal

@objc public final class RDDDatadogHost: NSObject {
  @objc public static func qualifyNativeConfiguration() {
    precondition(!Datadog.isInitialized())
    let original=Datadog.verbosityLevel
    for value in [CoreLoggerLevel.debug, .warn, .error, .critical] {
      Datadog.verbosityLevel=value
      precondition(Datadog.verbosityLevel == value)
    }
    Datadog.verbosityLevel=original
    var config=Datadog.Configuration(clientToken:"rdd-inert-no-upload-authority",env:"local-test")
    config.rddUseUnavailableTransportForLocalTesting()
    precondition(config.rddCheckUnavailableTransportForLocalTesting())
    NSLog("RDD_DATADOG_TRANSPORT_CONTROL_PASS externalRejected=1 localRejected=1 clockLocal=1")
  }
}
final class RDDDatadogContextProbe: DatadogFeature, FeatureMessageReceiver {
  static let name = "rdd-local-context-control"
  var messageReceiver: FeatureMessageReceiver { self }
  func receive(message: FeatureMessage, from core: any DatadogCoreProtocol) -> Bool { false }
}
