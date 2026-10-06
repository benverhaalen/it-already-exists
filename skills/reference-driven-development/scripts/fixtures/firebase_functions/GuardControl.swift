import Foundation

// No requests: vary one property of a permitted URL for each rejection control.
func rddRunCallableGuardControl() throws -> Int {
  guard ProcessInfo.processInfo.environment["RDD_FUNCTIONS_LOCAL_ONLY"] == "1" else {
    throw NSError(domain: "RDDCallableGuardControl", code: 1)
  }
  let base = "http://127.0.0.1:5006/demo-rdd-accounts/us-central1/rddEcho"
  for endpoint in [base, base.replacingOccurrences(of: "rddEcho", with: "A" + String(repeating: "x", count: 99))] {
    try rddQualifyLocalCallableURL(URL(string: endpoint)!)
  }
  let denied = [
    base.replacingOccurrences(of: "http:", with: "https:"),
    base.replacingOccurrences(of: "127.0.0.1", with: "example.invalid"),
    base.replacingOccurrences(of: "127.0.0.1", with: "localhost"),
    base.replacingOccurrences(of: ":5006", with: ":5007"),
    base.replacingOccurrences(of: ":5006", with: ""),
    base.replacingOccurrences(of: "demo-rdd-accounts", with: "other-project"),
    base.replacingOccurrences(of: "us-central1", with: "US-central1"),
    base.replacingOccurrences(of: "us-central1", with: "us--central1"),
    base.replacingOccurrences(of: "rddEcho", with: "1Echo"),
    base.replacingOccurrences(of: "rddEcho", with: "A" + String(repeating: "x", count: 100)),
    base.replacingOccurrences(of: "rddEcho", with: ""),
    base + "/extra",
    base + "?override=1",
    base + "?",
    base + "#fragment",
    base + "#",
    base.replacingOccurrences(of: "127.0.0.1", with: "user@127.0.0.1"),
    base.replacingOccurrences(of: "127.0.0.1", with: ":password@127.0.0.1"),
    base + "%0A",
    base + "%0D",
    base + "%E2%80%A8",
    base + "%2Fextra"
  ]
  for endpoint in denied {
    guard let url = URL(string: endpoint) else {
      throw NSError(domain: "RDDCallableGuardControl", code: 2)
    }
    var rejected = false
    do { try rddQualifyLocalCallableURL(url) }
    catch {
      let failure = error as NSError
      rejected = failure.domain == "RDDLocalFunctionsTransport" && failure.code == 1
    }
    guard rejected else { throw NSError(domain: "RDDCallableGuardControl", code: 3) }
  }
  return denied.count
}

#if RDD_CALLABLE_GUARD_STANDALONE
@main enum RDDCallableGuardControlMain {
  static func main() throws {
    let count = try rddRunCallableGuardControl()
    print("RDD_CALLABLE_GUARD_CONTROL_PASS allowed=2 rejected=\(count) requests=0")
  }
}
#endif
