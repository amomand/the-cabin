#import "PythonBridge.h"

#import <Python/Python.h>
#import <unistd.h>

static NSString * const PythonBridgeErrorDomain = @"uk.co.amomand.thecabin.python";

@interface PythonBridge () {
    dispatch_queue_t _queue;
    PyObject *_engine;
    BOOL _initialized;
    NSError *_initializationError;
}
@end

@implementation PythonBridge

+ (instancetype)sharedBridge {
    static PythonBridge *bridge;
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        bridge = [[PythonBridge alloc] initPrivate];
    });
    return bridge;
}

- (instancetype)init {
    [NSException raise:NSInternalInconsistencyException
                format:@"Use +sharedBridge"];
    return nil;
}

- (instancetype)initPrivate {
    self = [super init];
    if (self) {
        _queue = dispatch_queue_create(
            "uk.co.amomand.thecabin.python",
            DISPATCH_QUEUE_SERIAL
        );
    }
    return self;
}

- (void)performRequest:(NSString *)request
            completion:(void (^)(NSString * _Nullable, NSError * _Nullable))completion {
    dispatch_async(_queue, ^{
        NSError *bootError = [self initializeIfNeeded];
        if (bootError != nil) {
            completion(nil, bootError);
            return;
        }

        PyGILState_STATE gil = PyGILState_Ensure();
        PyObject *response = PyObject_CallMethod(
            self->_engine,
            "dispatch",
            "s",
            request.UTF8String
        );
        if (response == NULL || !PyUnicode_Check(response)) {
            PyErr_Clear();
            Py_XDECREF(response);
            PyGILState_Release(gil);
            completion(nil, [self error:@"The embedded engine did not return JSON."]);
            return;
        }
        const char *utf8 = PyUnicode_AsUTF8(response);
        NSString *result = utf8 == NULL ? nil : [NSString stringWithUTF8String:utf8];
        Py_DECREF(response);
        PyGILState_Release(gil);
        if (result == nil) {
            completion(nil, [self error:@"The embedded engine returned unreadable JSON."]);
            return;
        }
        completion(result, nil);
    });
}

- (NSError *)initializeIfNeeded {
    if (_initialized) {
        return nil;
    }
    if (_initializationError != nil) {
        return _initializationError;
    }

    NSString *resourcePath = NSBundle.mainBundle.resourcePath;
    NSString *pythonHome = [resourcePath stringByAppendingPathComponent:@"python"];
    NSString *appPath = [resourcePath stringByAppendingPathComponent:@"app"];
    NSString *packagesPath = [resourcePath stringByAppendingPathComponent:@"app_packages"];
    NSURL *supportBase = [[[NSFileManager defaultManager]
        URLsForDirectory:NSApplicationSupportDirectory
        inDomains:NSUserDomainMask] firstObject];
    NSURL *supportURL = [[supportBase URLByAppendingPathComponent:@"TheCabin" isDirectory:YES]
        URLByAppendingPathComponent:@"Engine" isDirectory:YES];
    NSError *directoryError = nil;
    if (![[NSFileManager defaultManager]
            createDirectoryAtURL:supportURL
            withIntermediateDirectories:YES
            attributes:nil
            error:&directoryError]) {
        _initializationError = directoryError;
        return _initializationError;
    }

    setenv("CABIN_MODEL_TRANSPORT", "direct-httpx", true);
    setenv("CABIN_SAVE_DIR", [[supportURL.path stringByAppendingPathComponent:@"saves"] UTF8String], true);
    setenv("CABIN_LOG_DIR", [[supportURL.path stringByAppendingPathComponent:@"logs"] UTF8String], true);
    setenv("NO_COLOR", "1", true);
    setenv("PYTHON_COLORS", "0", true);

    PyPreConfig preconfig;
    PyPreConfig_InitIsolatedConfig(&preconfig);
    preconfig.utf8_mode = 1;
    PyStatus status = Py_PreInitialize(&preconfig);
    if (PyStatus_Exception(status)) {
        return [self failInitialization:@"Embedded Python pre-initialization failed."];
    }

    PyConfig config;
    PyConfig_InitIsolatedConfig(&config);
    config.buffered_stdio = 0;
    config.write_bytecode = 0;
    wchar_t *home = Py_DecodeLocale(pythonHome.UTF8String, NULL);
    if (home == NULL) {
        PyConfig_Clear(&config);
        return [self failInitialization:@"Embedded Python home was unreadable."];
    }
    status = PyConfig_SetString(&config, &config.home, home);
    PyMem_RawFree(home);
    if (!PyStatus_Exception(status)) {
        status = PyConfig_Read(&config);
    }
    if (!PyStatus_Exception(status)) {
        status = Py_InitializeFromConfig(&config);
    }
    PyConfig_Clear(&config);
    if (PyStatus_Exception(status)) {
        return [self failInitialization:@"Embedded Python initialization failed."];
    }

    PyObject *site = PyImport_ImportModule("site");
    PyObject *addSiteDir = site == NULL ? NULL : PyObject_GetAttrString(site, "addsitedir");
    PyObject *packagePath = PyUnicode_FromString(packagesPath.UTF8String);
    PyObject *siteResult = (addSiteDir != NULL && packagePath != NULL)
        ? PyObject_CallOneArg(addSiteDir, packagePath)
        : NULL;
    Py_XDECREF(packagePath);
    Py_XDECREF(addSiteDir);
    Py_XDECREF(site);
    if (siteResult == NULL) {
        PyErr_Clear();
        return [self failInitialization:@"Embedded Python packages could not be loaded."];
    }
    Py_DECREF(siteResult);

    PyObject *sysPath = PySys_GetObject("path"); // borrowed
    PyObject *pythonAppPath = PyUnicode_FromString(appPath.UTF8String);
    if (sysPath == NULL || pythonAppPath == NULL || PyList_Insert(sysPath, 0, pythonAppPath) != 0) {
        Py_XDECREF(pythonAppPath);
        PyErr_Clear();
        return [self failInitialization:@"Embedded game code could not be loaded."];
    }
    Py_DECREF(pythonAppPath);
    if (chdir(appPath.UTF8String) != 0) {
        return [self failInitialization:@"Embedded game directory could not be opened."];
    }

    PyObject *module = PyImport_ImportModule("server.local_engine");
    PyObject *engineClass = module == NULL ? NULL : PyObject_GetAttrString(module, "LocalEngine");
    PyObject *arguments = Py_BuildValue("(s)", supportURL.path.UTF8String);
    _engine = (engineClass != NULL && arguments != NULL)
        ? PyObject_CallObject(engineClass, arguments)
        : NULL;
    Py_XDECREF(arguments);
    Py_XDECREF(engineClass);
    Py_XDECREF(module);
    if (_engine == NULL) {
        PyErr_Clear();
        return [self failInitialization:@"Embedded game engine could not be opened."];
    }

    _initialized = YES;
    PyEval_SaveThread();
    return nil;
}

- (NSError *)failInitialization:(NSString *)message {
    PyErr_Clear();
    NSLog(@"CABIN_EMBEDDED_PYTHON_FAILED: %@", message);
    _initializationError = [self error:message];
    return _initializationError;
}

- (NSError *)error:(NSString *)message {
    return [NSError errorWithDomain:PythonBridgeErrorDomain
                               code:1
                           userInfo:@{NSLocalizedDescriptionKey: message}];
}

@end
