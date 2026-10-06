#import <UIKit/UIKit.h>
@import FirebaseCore;
@import FirebaseFirestore;
#import "LocalFirestoreSettings.h"
@interface RDDDelegate:UIResponder<UIApplicationDelegate>
@property(nonatomic,strong)UIWindow *window;
@property(nonatomic,strong)FIRFirestore *store;
@property(nonatomic,strong)id<FIRListenerRegistration> listener;
@end
@implementation RDDDelegate
-(BOOL)application:(UIApplication*)application didFinishLaunchingWithOptions:(NSDictionary*)options {
 self.window=[[UIWindow alloc]initWithFrame:UIScreen.mainScreen.bounds];UIViewController *vc=[UIViewController new];vc.view.backgroundColor=UIColor.whiteColor;self.window.rootViewController=vc;[self.window makeKeyAndVisible];
 FIRFirestoreSettings *probe=[FIRFirestoreSettings new];
 for(NSString *host in @[@"1.1.1.1",@"localhost",@"127.0.0.1.example",@"::ffff:127.0.0.1"]){
   BOOL rejected=NO;@try{RDDConfigureLocalFirestoreSettings(probe,host,8082);}@catch(NSException *error){rejected=YES;}
   if(!rejected){NSLog(@"RDD_FIRESTORE_EXTERNAL_HOST_FAIL");return YES;}
 }
 RDDConfigureLocalFirestoreSettings(probe,@"::1",8082);
 if(![probe.host isEqualToString:@"[::1]:8082"]||probe.sslEnabled){NSLog(@"RDD_FIRESTORE_IPV6_SETTINGS_FAIL");return YES;}
 NSLog(@"RDD_FIRESTORE_HOST_VALIDATION_PASS ipv6Settings=1 rejectedExternalAndDNS=1");
 for(NSString *className in @[@"FIRAuth",@"FIRAppCheck",@"FIRInstallations"]){if(NSClassFromString(className)){NSLog(@"RDD_FIRESTORE_UNEXPECTED_SERVICE_CLASS_FAIL");return YES;}}
 NSLog(@"RDD_FIRESTORE_SELECTED_PRODUCTS_PASS auth=0 appCheck=0 installations=0");
 FIRApp *app;FIROptions *config=[[FIROptions alloc]initWithGoogleAppID:@"1:1234567890:android:0123456789abcdef" GCMSenderID:@"1234567890"];config.projectID=@"demo-rdd-accounts";[FIRApp configureWithName:@"RDDLocalFirestore" options:config];app=[FIRApp appNamed:@"RDDLocalFirestore"];app.dataCollectionDefaultEnabled=NO;
 self.store=[FIRFirestore firestoreForApp:app];[self.store useEmulatorWithHost:@"127.0.0.1" port:8082]; FIRFirestoreSettings *settings=self.store.settings;RDDConfigureLocalFirestoreSettings(settings,@"127.0.0.1",8082);self.store.settings=settings;
 NSLog(@"RDD_FIRESTORE_CONTROL endpoint=%@ ssl=%d",self.store.settings.host,self.store.settings.sslEnabled);
 if(![self.store.settings.host isEqualToString:@"127.0.0.1:8082"]||self.store.settings.sslEnabled){NSLog(@"RDD_FIRESTORE_ENDPOINT_FAIL");return YES;}
 FIRDocumentReference *doc=[self.store documentWithPath:@"compatibilityControls/native-ios"];
 __block BOOL received=NO;
 self.listener=[doc addSnapshotListenerWithIncludeMetadataChanges:YES listener:^(FIRDocumentSnapshot *snapshot,NSError *error){
 if(error){NSLog(@"RDD_FIRESTORE_LISTENER_FAIL code=%ld",(long)error.code);return;}
 if([snapshot.data[@"value"] isEqual:@(9007199254740991LL)]&&!snapshot.metadata.hasPendingWrites&&!snapshot.metadata.isFromCache&&!received){received=YES;NSLog(@"RDD_FIRESTORE_LISTENER_PASS server=1 int64=1");[self.listener remove];}
 }];
 [doc setData:@{@"value":@(9007199254740991LL),@"scope":@"local-only"} completion:^(NSError *error){
 if(error){NSLog(@"RDD_FIRESTORE_WRITE_FAIL code=%ld",(long)error.code);return;}NSLog(@"RDD_FIRESTORE_LOCAL_WRITE_PASS");
 [doc getDocumentWithSource:FIRFirestoreSourceServer completion:^(FIRDocumentSnapshot *snapshot,NSError *readError){BOOL pass=!readError&&[snapshot.data[@"value"] isEqual:@(9007199254740991LL)]&&!snapshot.metadata.isFromCache;NSLog(@"RDD_FIRESTORE_SERVER_READ_%@",pass?@"PASS":@"FAIL");}];
 }];
 return YES;
}
@end
int main(int argc,char **argv){@autoreleasepool{return UIApplicationMain(argc,argv,nil,NSStringFromClass(RDDDelegate.class));}}
