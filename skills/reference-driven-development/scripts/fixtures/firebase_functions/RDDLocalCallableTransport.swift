import Foundation

// Opt-in endpoint qualification before native token acquisition or request construction.
// This does not intercept redirects or establish a whole-process network boundary.
func rddQualifyLocalCallableURL(_ url: URL) throws {
  guard ProcessInfo.processInfo.environment["RDD_FUNCTIONS_LOCAL_ONLY"] == "1" else { return }
  let components=URLComponents(url:url,resolvingAgainstBaseURL:false)
  let path=url.path
  let permittedPath=path.range(of:"^/demo-rdd-accounts/[a-z0-9]+(?:-[a-z0-9]+)*/[A-Za-z][A-Za-z0-9_-]{0,99}$",options:.regularExpression) != nil
  guard url.scheme == "http", url.host == "127.0.0.1", url.port == 5006,
        url.user == nil, url.password == nil, components?.query == nil,
        components?.fragment == nil, permittedPath else {
    throw NSError(domain:"RDDLocalFunctionsTransport",code:1,
                  userInfo:[NSLocalizedDescriptionKey:"Callable endpoint is outside the local test namespace"])
  }
}
