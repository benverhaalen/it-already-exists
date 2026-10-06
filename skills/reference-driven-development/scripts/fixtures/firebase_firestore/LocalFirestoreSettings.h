#import <Foundation/Foundation.h>
@import FirebaseFirestore;
#include <arpa/inet.h>

// This controls Firestore endpoints only. It is not a process network sandbox.
static inline void RDDConfigureLocalFirestoreSettings(FIRFirestoreSettings *settings,
                                                       NSString *host, NSInteger port) {
  struct in_addr v4;
  struct in6_addr v6;
  const char *text = host.UTF8String;
  BOOL ipv4 = text && inet_pton(AF_INET, text, &v4) == 1 && (ntohl(v4.s_addr) >> 24) == 127;
  BOOL ipv6 = text && inet_pton(AF_INET6, text, &v6) == 1 && IN6_IS_ADDR_LOOPBACK(&v6);
  if (!settings || (!ipv4 && !ipv6) || port < 1 || port > 65535) {
    @throw [NSException exceptionWithName:NSInvalidArgumentException
                                 reason:@"Firestore test authority requires numeric loopback and a valid port"
                               userInfo:nil];
  }
  settings.host = ipv6 ? [NSString stringWithFormat:@"[%@]:%ld",host,(long)port]
                       : [NSString stringWithFormat:@"%@:%ld",host,(long)port];
  settings.sslEnabled = NO;
}
