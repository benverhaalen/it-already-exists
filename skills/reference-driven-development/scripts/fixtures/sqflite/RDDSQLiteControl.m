#import "RDDSQLiteControl.h"
#import "SQLitePlugin/SqflitePlugin.h"
#import <Flutter/Flutter.h>

static id call(SqflitePlugin *plugin, NSString *method, NSDictionary *args) {
 FlutterStandardMethodCodec *codec = [FlutterStandardMethodCodec sharedInstance];
 FlutterMethodCall *request = [codec decodeMethodCall:[codec encodeMethodCall:[FlutterMethodCall methodCallWithMethodName:method arguments:args]]];
 dispatch_semaphore_t semaphore = dispatch_semaphore_create(0);
 __block id result;
 [plugin handleMethodCall:request result:^(id value) { result=value;dispatch_semaphore_signal(semaphore); }];
 if (dispatch_semaphore_wait(semaphore,dispatch_time(DISPATCH_TIME_NOW,3*NSEC_PER_SEC)))
  @throw [NSException exceptionWithName:@"SQLiteControlTimeout" reason:method userInfo:nil];
 if ([result isKindOfClass:[FlutterError class]]) return result;
 return [codec decodeEnvelope:[codec encodeSuccessEnvelope:result]];
}
static id checked(SqflitePlugin *plugin, NSString *method, NSDictionary *args) {
 id result=call(plugin,method,args);
 if ([result isKindOfClass:[FlutterError class]])
  @throw [NSException exceptionWithName:@"SQLiteControlError" reason:method userInfo:nil];
 return result;
}
static void require(BOOL value) {
 if (!value) @throw [NSException exceptionWithName:@"SQLiteControlMismatch" reason:@"native result mismatch" userInfo:nil];
}
BOOL RDDQualifySQLite(void) {
 SqflitePlugin *plugin=[SqflitePlugin new];
 NSString *path=[NSTemporaryDirectory() stringByAppendingPathComponent:[@"rdd-sqlite-control-" stringByAppendingString:NSUUID.UUID.UUIDString]];
 NSNumber *databaseId=nil;
 @try {
  NSDictionary *opened=checked(plugin,@"openDatabase",@{@"path":path,@"singleInstance":@NO});databaseId=opened[@"id"];require(databaseId!=nil);
  checked(plugin,@"execute",@{@"id":databaseId,@"sql":@"CREATE TABLE probe (n INTEGER, text_value TEXT, bytes_value BLOB, nullable TEXT)",@"arguments":@[]});
  NSData *bytes=[NSData dataWithBytes:(unsigned char[]){0,127,255} length:3];
  checked(plugin,@"insert",@{@"id":databaseId,@"sql":@"INSERT INTO probe VALUES (?,?,?,?)",@"arguments":@[@9007199254740991LL,@"native-roundtrip",[FlutterStandardTypedData typedDataWithBytes:bytes],NSNull.null]});
  NSDictionary *queried=checked(plugin,@"query",@{@"id":databaseId,@"sql":@"SELECT n,text_value,bytes_value,nullable FROM probe",@"arguments":@[]});
  NSArray *row=[queried[@"rows"] firstObject];require([queried[@"columns"] count]==4 && row.count==4);
  require([row[0] longLongValue]==9007199254740991LL && [row[1] isEqual:@"native-roundtrip"] && [[(FlutterStandardTypedData*)row[2] data] isEqual:bytes] && row[3]==NSNull.null);
  checked(plugin,@"execute",@{@"id":databaseId,@"sql":@"BEGIN IMMEDIATE",@"arguments":@[],@"inTransaction":@YES});
  checked(plugin,@"insert",@{@"id":databaseId,@"sql":@"INSERT INTO probe(n) VALUES(2)",@"arguments":@[]});
  checked(plugin,@"execute",@{@"id":databaseId,@"sql":@"ROLLBACK",@"arguments":@[],@"inTransaction":@NO});
  checked(plugin,@"closeDatabase",@{@"id":databaseId});databaseId=nil;
  opened=checked(plugin,@"openDatabase",@{@"path":path,@"singleInstance":@NO});databaseId=opened[@"id"];
  queried=checked(plugin,@"query",@{@"id":databaseId,@"sql":@"SELECT COUNT(*) FROM probe",@"arguments":@[]});require([queried[@"rows"][0][0] intValue]==1);
  id error=call(plugin,@"query",@{@"id":databaseId,@"sql":@"SELECT * FROM missing_table",@"arguments":@[]});require([error isKindOfClass:FlutterError.class] && [[(FlutterError*)error code] isEqual:@"sqlite_error"]);
  checked(plugin,@"closeDatabase",@{@"id":databaseId});databaseId=nil;
  checked(plugin,@"deleteDatabase",@{@"path":path});require(![NSFileManager.defaultManager fileExistsAtPath:path]);
  NSLog(@"RDD_SQLITE_NATIVE_CONTROL_PASS codec=1 int64=1 text=1 blob=1 null=1 rollback=1 reopen=1 error=1 cleanup=1");return YES;
 } @catch(NSException *error) {
  NSLog(@"RDD_SQLITE_NATIVE_CONTROL_FAILED %@",error.name);
  if(databaseId) call(plugin,@"closeDatabase",@{@"id":databaseId});
  call(plugin,@"deleteDatabase",@{@"path":path});return NO;
 }
}
