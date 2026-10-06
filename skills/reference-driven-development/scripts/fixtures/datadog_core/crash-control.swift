import DatadogInternal
public extension CrashReporting {
    static func rddIsEnabledForLocalTesting(in core: DatadogCoreProtocol = CoreRegistry.default) -> Bool {
        core.feature(named: CrashReportingFeature.name, type: CrashReportingFeature.self) != nil
    }
}
