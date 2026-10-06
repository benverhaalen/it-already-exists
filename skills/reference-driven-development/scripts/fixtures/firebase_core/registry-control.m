// Authored local control. Link FirebaseCore 12.19.0; no other Firebase product.
#import <FirebaseCore/FirebaseCore.h>
@interface FIRApp (RDDValidation)
+ (BOOL)validateAppID:(NSString *)appID;
@end
BOOL RDDQualifyAndroidCoreRegistry(void) {
 BOOL validation=[FIRApp validateAppID:@"1:123456:android:abcdef1234567890"] &&
 [FIRApp validateAppID:@"1:123456:ios:abcdef1234567890"] &&
 ![FIRApp validateAppID:@"invalid"];
 if (!validation || FIRApp.allApps.count) return NO;
 FIROptions *options=[[FIROptions alloc] initWithGoogleAppID:@"1:123456:android:abcdef1234567890" GCMSenderID:@"123456"];
 options.APIKey=@"rdd_local_synthetic_not_a_credential";
 options.projectID=@"demo-rdd-core";
 [FIRApp configureWithName:@"rdd-local" options:options];
 FIRApp *app=[FIRApp appNamed:@"rdd-local"];
 BOOL identity=[app.options.googleAppID isEqualToString:options.googleAppID];
 app.dataCollectionDefaultEnabled=NO;
 BOOL collection=!app.isDataCollectionDefaultEnabled;
 NSLog(@"RDD_CORE_REGISTRY_CONTROL identityPreserved=%d dataCollectionDisabled=%d",identity,collection);
 [app deleteApp:^(BOOL success){NSLog(@"RDD_CORE_DELETE_CONTROL deleted=%d registryEmpty=%d",success,FIRApp.allApps.count==0);}];
 return identity && collection;
}
