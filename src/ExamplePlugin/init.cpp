#include <ExamplePlugin/init.h>
#include <sofa/core/ObjectFactory.h>

namespace exampleplugin
{

void initializePlugin() 
{
    static bool first = true;
    if (first) {
        first = false;
        // Register components here
    }
}

}

extern "C" 
{
    EXAMPLEPLUGIN_API void initExternalModule() 
    {
        exampleplugin::initializePlugin();
    }

    EXAMPLEPLUGIN_API const char* getModuleName() 
    {
        return exampleplugin::MODULE_NAME;
    }

    EXAMPLEPLUGIN_API const char* getModuleVersion() 
    {
        return exampleplugin::MODULE_VERSION;
    }

    EXAMPLEPLUGIN_API const char* getModuleLicense() 
    {
        return "LGPL";
    }

    EXAMPLEPLUGIN_API const char* getModuleDescription() 
    {
        return "SOFA plugin for ExamplePlugin";
    }
}
