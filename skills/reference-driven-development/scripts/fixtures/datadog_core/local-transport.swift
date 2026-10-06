import Foundation

// Explicit test-host policy: replace the SDK's HTTP factory and NTP provider.
// Applies only to cores initialized from this configuration, not the process.
private final class RDDRejectedHTTPClient: HTTPClient {
    func send(request: URLRequest, delegate: URLSessionTaskDelegate?, completion: @escaping (Result<HTTPURLResponse, Error>) -> Void) {
        completion(.failure(URLError(.notConnectedToInternet)))
    }
}
private final class RDDDeviceClock: ServerDateProvider {
    func synchronize(update: @escaping (TimeInterval) -> Void) { update(0) }
}
public extension Datadog.Configuration {
    mutating func rddUseUnavailableTransportForLocalTesting() {
        httpClientFactory = { _ in RDDRejectedHTTPClient() }
        serverDateProvider = RDDDeviceClock()
    }
    func rddCheckUnavailableTransportForLocalTesting() -> Bool {
        let client = httpClientFactory(nil)
        var count = 0
        for address in ["https://example.invalid/rdd-control", "http://127.0.0.1:8084/rdd-control"] {
            client.send(request: URLRequest(url: URL(string: address)!)) { result in
                if case .failure(let error) = result, (error as? URLError)?.code == .notConnectedToInternet { count += 1 }
            }
        }
        var clockIsLocal = false
        if serverDateProvider is RDDDeviceClock {
            serverDateProvider.synchronize { clockIsLocal = $0 == 0 }
        }
        return count == 2 && clockIsLocal
    }
}
