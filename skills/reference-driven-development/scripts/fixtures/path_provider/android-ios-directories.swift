import Foundation
import Flutter

// Android Pigeon channel names with native iOS directory semantics, following
// path_provider_android 2.2.22 and path_provider_foundation 2.4.4.
@objc public final class RDDPathProviderHost: NSObject {
  private static let directories: [String: FileManager.SearchPathDirectory] = [
    "getTemporaryPath": .cachesDirectory,
    "getApplicationCachePath": .cachesDirectory,
    "getApplicationDocumentsPath": .documentDirectory,
    "getApplicationSupportPath": .applicationSupportDirectory
  ]
  private static func directory(_ method: String) throws -> URL {
    guard let type = directories[method] else {
      throw NSError(domain: "UnsupportedPathProviderMethod", code: 1)
    }
    return try FileManager.default.url(for: type, in: .userDomainMask,
                                       appropriateFor: nil, create: true)
  }
  private static func qualify() throws {
    let marker = Data("native-directory-roundtrip".utf8)
    for method in directories.keys.sorted() {
      let dir = try directory(method)
      let probe = dir.appendingPathComponent("rdd-path-control-" + UUID().uuidString)
      defer { try? FileManager.default.removeItem(at: probe) }
      try marker.write(to: probe, options: .atomic)
      guard try Data(contentsOf: probe) == marker,
            dir.path.hasPrefix(NSHomeDirectory() + "/") else {
        throw NSError(domain: "DirectoryControlFailed", code: 1)
      }
    }
    let temporary = try directory("getTemporaryPath")
    let cache = try directory("getApplicationCachePath")
    let documents = try directory("getApplicationDocumentsPath")
    let support = try directory("getApplicationSupportPath")
    guard temporary == cache, documents != support else {
      throw NSError(domain: "DirectoryMappingControlFailed", code: 1)
    }
    NSLog("RDD_PATH_NATIVE_CONTROL_PASS directories=4 writeRead=1 container=1 cacheAlias=1")
  }
  @objc public static func registerMessenger(_ messenger: FlutterBinaryMessenger) {
    do { try qualify() } catch {
      NSLog("RDD_PATH_NATIVE_CONTROL_FAILED %@", error.localizedDescription)
      return
    }
    for method in directories.keys {
      let channel = FlutterBasicMessageChannel(
        name: "dev.flutter.pigeon.path_provider_android.PathProviderApi." + method,
        binaryMessenger: messenger, codec: FlutterStandardMessageCodec.sharedInstance())
      channel.setMessageHandler { message, reply in
        // These generated methods send null, not an argument list.
        guard message == nil || message is NSNull else {
          reply(["argument-error", "Expected a null directory request", NSNull()]); return
        }
        do {
          let path = try directory(method).path
          NSLog("RDD_PATH_NATIVE_CALL %@", method)
          reply([path])
        } catch { reply(["directory-error", error.localizedDescription, NSNull()]) }
      }
    }
    // Android shared/external storage requires a separate property transfer;
    // do not imply that an iOS sandbox directory is shared external storage.
  }
}
