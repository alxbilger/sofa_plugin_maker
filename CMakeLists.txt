# CMakeLists.txt for ExamplePlugin plugin
cmake_minimum_required(VERSION 3.12)
project(ExamplePlugin VERSION 1.0 LANGUAGES CXX)

find_package(Sofa.Core REQUIRED)

set(HEADER_FILES
    src/ExamplePlugin/config.h.in
    src/ExamplePlugin/init.h
)

set(SOURCE_FILES
    src/ExamplePlugin/init.cpp
)

add_library(${PROJECT_NAME} SHARED ${HEADER_FILES} ${SOURCE_FILES})
target_link_libraries(${PROJECT_NAME} PUBLIC Sofa.Core)

sofa_create_package_with_targets(
    PACKAGE_NAME ${PROJECT_NAME}
    PACKAGE_VERSION ${PROJECT_VERSION}
    TARGETS ${PROJECT_NAME} AUTO_SET_TARGET_PROPERTIES
    INCLUDE_SOURCE_DIR "src"
    INCLUDE_INSTALL_DIR ${PROJECT_NAME}
    RELOCATABLE "plugins"
    )
    
cmake_dependent_option(EXAMPLEPLUGIN_BUILD_TESTS "Compile the automatic tests" ON "SOFA_BUILD_TESTS OR NOT DEFINED SOFA_BUILD_TESTS" OFF)
if(EXAMPLEPLUGIN_BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()
