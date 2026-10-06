import Foundation
import Security

/// Qualifies the calling app's default Keychain group using one owned item.
/// No authentication state, shared group, accessibility or device claim.
@discardableResult
func RDDQualifyKeychain() -> Bool {
  let service = "rdd-keychain-control-" + UUID().uuidString
  let value = Data("owned-control".utf8)
  let query: [String: Any] = [
    kSecClass as String: kSecClassGenericPassword,
    kSecAttrService as String: service,
    kSecAttrAccount as String: "control",
    kSecValueData as String: value
  ]
  let added = SecItemAdd(query as CFDictionary, nil)
  guard added == errSecSuccess else {
    NSLog("RDD_KEYCHAIN_CONTROL_FAIL operation=add status=%d", added)
    return false
  }
  var lookup = query
  lookup.removeValue(forKey: kSecValueData as String)
  lookup[kSecReturnData as String] = true
  var found: CFTypeRef?
  let copied = SecItemCopyMatching(lookup as CFDictionary, &found)
  lookup.removeValue(forKey: kSecReturnData as String)
  let deleted = SecItemDelete(lookup as CFDictionary)
  guard copied == errSecSuccess, (found as? Data) == value,
        deleted == errSecSuccess else {
    NSLog("RDD_KEYCHAIN_CONTROL_FAIL readStatus=%d deleteStatus=%d", copied, deleted)
    return false
  }
  NSLog("RDD_KEYCHAIN_CONTROL_PASS add=1 read=1 value=1 delete=1")
  return true
}
