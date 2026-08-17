#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

/// Owns the one embedded CPython interpreter and serialises every C-API call.
@interface PythonBridge : NSObject

+ (instancetype)sharedBridge;

- (void)performRequest:(NSString *)request
            completion:(void (^)(NSString * _Nullable response,
                                  NSError * _Nullable error))completion;

@end

NS_ASSUME_NONNULL_END
