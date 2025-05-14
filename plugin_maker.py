import sys
import re
import os

def print_help():
    print("Usage: python plugin_maker.py <plugin_name> <path>")
    print("  <plugin_name>: Name of the plugin (alphanumeric, hyphens, underscores only)")
    print("  <path>: Path where the plugin folder will be created")
    print("\nThis script creates a SOFA plugin template with the necessary files and folder structure.")

def create_file(file_path, content):
    with open(file_path, 'w') as f:
        f.write(content)
    print(f"Created file: {file_path}")

def main():
    if len(sys.argv) != 3:
        print("Error: Please provide exactly two command line arguments: plugin_name and path")
        print_help()
        sys.exit(1)

    plugin_name = sys.argv[1]
    path = sys.argv[2]

    # Check if string contains only allowed characters (alphanumeric, hyphen, and underscore)
    if not re.match(r'^[a-zA-Z0-9\-_]+$', plugin_name):
        print("Error: Plugin name can only contain letters, numbers, hyphens (-) and underscores (_)")
        sys.exit(1)

    # Check if the provided path exists
    if not os.path.exists(path):
        print(f"Error: The provided path '{path}' does not exist")
        sys.exit(1)

    # Check if a folder with the plugin_name already exists in the path
    plugin_path = os.path.join(path, plugin_name)
    if os.path.exists(plugin_path):
        print(f"Error: A folder named '{plugin_name}' already exists in '{path}'")
        sys.exit(1)

    # If we get here, both arguments are valid
    print(f"Plugin name '{plugin_name}' is valid")
    print(f"Path '{path}' is valid")

    upper_plugin_name = plugin_name.upper()

    # Create the main plugin folder
    os.makedirs(plugin_path)
    print(f"Created folder: {plugin_path}")

    # Create CMakeLists.txt
    cmake_content = f"""# CMakeLists.txt for {plugin_name} plugin
cmake_minimum_required(VERSION 3.12)
project({plugin_name} VERSION 1.0 LANGUAGES CXX)

find_package(Sofa.Core REQUIRED)

set(HEADER_FILES
    src/{plugin_name}/config.h.in
    src/{plugin_name}/init.h
)

set(SOURCE_FILES
    src/{plugin_name}/init.cpp
)

add_library(${{PROJECT_NAME}} SHARED ${{HEADER_FILES}} ${{SOURCE_FILES}})
target_link_libraries(${{PROJECT_NAME}} PUBLIC Sofa.Core)

sofa_create_package_with_targets(
    PACKAGE_NAME ${{PROJECT_NAME}}
    PACKAGE_VERSION ${{PROJECT_VERSION}}
    TARGETS ${{PROJECT_NAME}} AUTO_SET_TARGET_PROPERTIES
    INCLUDE_SOURCE_DIR "src"
    INCLUDE_INSTALL_DIR ${{PROJECT_NAME}}
    RELOCATABLE "plugins"
    )
    
cmake_dependent_option({upper_plugin_name}_BUILD_TESTS "Compile the automatic tests" ON "SOFA_BUILD_TESTS OR NOT DEFINED SOFA_BUILD_TESTS" OFF)
if({upper_plugin_name}_BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()
"""
    create_file(os.path.join(plugin_path, "CMakeLists.txt"), cmake_content)

    # Create Config.cmake.in
    config_cmake_content = f"""# CMake package configuration file for the plugin @PROJECT_NAME@

@PACKAGE_GUARD@
@PACKAGE_INIT@

find_package(Sofa.Core QUIET REQUIRED)

if(NOT TARGET @PROJECT_NAME@)
    include("${{CMAKE_CURRENT_LIST_DIR}}/@PROJECT_NAME@Targets.cmake")
endif()

check_required_components({plugin_name})
"""
    create_file(os.path.join(plugin_path, f"{plugin_name}Config.cmake.in"), config_cmake_content)

    # Create README.md
    readme_content = f"""# {plugin_name}

## Description
A SOFA plugin created with plugin_maker.py.
"""
    create_file(os.path.join(plugin_path, "README.md"), readme_content)

    # Create .github folder
    github_path = os.path.join(plugin_path, ".github")
    os.makedirs(github_path)
    print(f"Created folder: {github_path}")

    # Create workflows folder
    workflows_path = os.path.join(github_path, "workflows")
    os.makedirs(workflows_path)
    print(f"Created folder: {workflows_path}")

    ci_workflow_content = f"""name: CI

on:
  workflow_dispatch:
  pull_request:
  push:

jobs:
  build-and-test:
    name: Run on ${{{{ matrix.os }}}} with SOFA ${{ matrix.sofa_branch }}}}
    runs-on: ${{{{ matrix.os }}}}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-22.04, macos-14, windows-2022]
        sofa_branch: [master]

    steps:
      - name: Setup SOFA and environment
        id: sofa
        uses: sofa-framework/sofa-setup-action@v5
        with:
          sofa_root: ${{ github.workspace }}}}/sofa
          sofa_version: ${{ matrix.sofa_branch }}}}
          sofa_scope: 'standard'
      
      - name: Checkout source code
        uses: actions/checkout@v2
        with:
          path: ${{{{ env.WORKSPACE_SRC_PATH }}}}        
      
      - name: Build and install
        shell: bash
        run: |
          if [[ "$RUNNER_OS" == "Windows" ]]; then
            cmd //c "${{{{ steps.sofa.outputs.vs_vsdevcmd }}}} \\
              && cd /d $WORKSPACE_BUILD_PATH \\
              && cmake \\
                  -GNinja \\
                  -DCMAKE_PREFIX_PATH="$SOFA_ROOT/lib/cmake" \\
                  -DCMAKE_BUILD_TYPE=Release \\
                  -DCMAKE_INSTALL_PREFIX="$WORKSPACE_INSTALL_PATH" \\
                  -DMPFR_LIBRARIES="$MPFR_LIBRARIES" \\
                  ../src \\
              && ninja -v install"
          else
            cd "$WORKSPACE_BUILD_PATH"
            ccache -z
            cmake \\
              -GNinja \\
              -DCMAKE_C_COMPILER_LAUNCHER=ccache \\
              -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \\
              -DCMAKE_PREFIX_PATH=$SOFA_ROOT/lib/cmake \\
              -DCMAKE_BUILD_TYPE=Release \\
              -DCMAKE_INSTALL_PREFIX="$WORKSPACE_INSTALL_PATH" \\
              ../src
            ninja -v install
            echo ${{CCACHE_BASEDIR}}
            ccache -s
          fi
      - name: Sanitize artifact name
        id: sanitize
        # This step removes special characters from the artifact name to ensure compatibility with upload-artifact
        # Characters removed: " : < > | * ? \\r \\n \\ /
        # Spaces are replaced with underscores
        # This sanitization prevents errors in artifact creation and retrieval
        shell: pwsh
        run: |
          $originalName = "{plugin_name}_${{{{ steps.sofa.outputs.run_branch }}}}_for-SOFA-${{{{ steps.sofa.outputs.sofa_version }}}}_${{{{ runner.os }}}}"
          $artifact_name = $originalName -replace '[":;<>|*?\\r\\n\\\\/]', '' -replace ' ', '_'
          echo "artifact_name=$artifact_name" >> $env:GITHUB_OUTPUT

      - name: Create artifact
        uses: actions/upload-artifact@v4.4.0
        with:
          name: ${{{{ steps.sanitize.outputs.artifact_name }}}}
          path: ${{{{ env.WORKSPACE_INSTALL_PATH }}}}

      - name: Install artifact
        uses: actions/download-artifact@v4.1.7
        with:
          name: ${{{{ steps.sanitize.outputs.artifact_name }}}}
          path: ${{{{ env.WORKSPACE_ARTIFACT_PATH }}}}
          
      - name: Set env vars for tests
        shell: bash
        run: |
          # Set env vars for tests
          if [[ "$RUNNER_OS" == "Windows" ]]; then
            echo "$WORKSPACE_ARTIFACT_PATH/lib" >> $GITHUB_PATH
            echo "$WORKSPACE_ARTIFACT_PATH/bin" >> $GITHUB_PATH
            echo "$SOFA_ROOT/plugins/SofaPython3/bin" >> $GITHUB_PATH
            echo "SOFA_PLUGIN_PATH=$WORKSPACE_ARTIFACT_PATH/bin" | tee -a $GITHUB_ENV
          else
            echo "SOFA_PLUGIN_PATH=$WORKSPACE_ARTIFACT_PATH/lib" | tee -a $GITHUB_ENV
          fi
          
          if [[ "$RUNNER_OS" == "macOS" ]]; then
            echo "DYLD_LIBRARY_PATH=$WORKSPACE_ARTIFACT_PATH/lib:$SOFA_ROOT/lib:$SOFA_ROOT/plugins/SofaPython3/lib:$DYLD_LIBRARY_PATH" | tee -a $GITHUB_ENV
          fi

          if [[ "$RUNNER_OS" == "Linux" ]]; then
            echo "LD_LIBRARY_PATH=$WORKSPACE_ARTIFACT_PATH/lib:$SOFA_ROOT/lib:$SOFA_ROOT/plugins/SofaPython3/lib:$LD_LIBRARY_PATH" | tee -a $GITHUB_ENV
          fi

      - name: Fetch, install and run Regression_test
        if: always()
        shell: bash
        run: |
          if [[ "$RUNNER_OS" != "macOS" ]]; then
            # Get regression from github releases
            mkdir -p "${{{{ runner.temp }}}}/regression_tmp/install"
            curl --output "${{{{ runner.temp }}}}/regression_tmp/${{RUNNER_OS}}.zip" -L https://github.com/sofa-framework/regression/releases/download/release-${{{{ steps.sofa.outputs.sofa_version }}}}/Regression_test_${{{{ steps.sofa.outputs.sofa_version }}}}_for-SOFA-${{{{ steps.sofa.outputs.sofa_version }}}}_${{RUNNER_OS}}.zip
            unzip -qq "${{ runner.temp }}/regression_tmp/${{RUNNER_OS}}.zip" -d "${{ runner.temp }}/regression_tmp/install"
            # Install it in the SOFA bin directory
            $SUDO mv "${{ runner.temp }}"/regression_tmp/install/Regression_*/bin/* "${{SOFA_ROOT}}/bin"
            chmod +x ${{SOFA_ROOT}}/bin/Regression_test${{{{ steps.sofa.outputs.exe }}}}
            # Setup mandatory env vars
            export REGRESSION_SCENES_DIR="${{WORKSPACE_SRC_PATH}}/examples"
            export REGRESSION_REFERENCES_DIR="${{WORKSPACE_SRC_PATH}}/regression/references"
            # Run regression test bench
            ${{SOFA_ROOT}}/bin/Regression_test${{{{ steps.sofa.outputs.exe }}}}
          else
            echo "Regression tests are not supported on the CI for macOS yet (TODO)"
          fi
  deploy:
    name: Deploy artifacts
    if: always()
    needs: [build-and-test]
    runs-on: ubuntu-latest
    continue-on-error: true
    steps:
      - name: Get artifacts
        uses: actions/download-artifact@v4.1.7
        with:
          path: artifacts

      - name: Zip artifacts
        shell: bash
        run: |
          cd $GITHUB_WORKSPACE/artifacts
          for artifact in *; do
            zip $artifact.zip -r $artifact/*
          done
      - name: Upload release
        uses: softprops/action-gh-release@v1
        with:
          name: ${{ github.ref_name }}
          tag_name: release-${{ github.ref_name }}
          fail_on_unmatched_files: false
          target_commitish: ${{ github.sha }}
          files: |
            artifacts/{plugin_name}_*_Linux.zip
            artifacts/{plugin_name}_*_Windows.zip
            artifacts/{plugin_name}_*_macOS.zip
"""
    create_file(os.path.join(workflows_path, "ci.yml"), ci_workflow_content)

    # Create examples folder
    examples_path = os.path.join(plugin_path, "examples")
    os.makedirs(examples_path)
    print(f"Created folder: {examples_path}")

    xml_path = os.path.join(examples_path, "xml")
    os.makedirs(xml_path)
    print(f"Created folder: {xml_path}")

    xml_example_content = f"""<?xml version="1.0" encoding="utf-8"?>
<Node name="root" dt="0.005" gravity="0 0 -9.81">
    <Node name="plugins">
        <RequiredPlugin name="{{plugin_name}}"/>
    </Node>
</Node>
"""
    create_file(os.path.join(xml_path, "example.scn"), xml_example_content)

    python_example_content = f"""import Sofa

def createScene(root_node):
    root_node.name = "root"
    root_node.dt = 0.005
    root_node.gravity = [0, 0, -9.81]

    plugins = root_node.addChild('plugins')

    plugins.addObject('RequiredPlugin', name="{plugin_name}")

"""
    create_file(os.path.join(examples_path, "example.py"), python_example_content)

    python_path = os.path.join(examples_path, "python")
    os.makedirs(python_path)
    print(f"Created folder: {python_path}")

    # Create regression folder
    regression_path = os.path.join(plugin_path, "regression")
    os.makedirs(regression_path)
    print(f"Created folder: {regression_path}")

    # Create references folder
    references_path = os.path.join(regression_path, "references")
    os.makedirs(references_path)
    print(f"Created folder: {references_path}")

    # Create src folder and plugin subfolder
    src_path = os.path.join(plugin_path, "src")
    os.makedirs(src_path)
    print(f"Created folder: {src_path}")

    plugin_src_path = os.path.join(src_path, plugin_name)
    os.makedirs(plugin_src_path)
    print(f"Created folder: {plugin_src_path}")

    # Create init.h
    init_h_content = f"""#pragma once
#include <{plugin_name}/config.h>

namespace {plugin_name}
{{

/** Initialize the {plugin_name} plugin */
void {upper_plugin_name}_API initializePlugin();

}}
"""
    create_file(os.path.join(plugin_src_path, "init.h"), init_h_content)

    # Create init.cpp
    init_cpp_content = f"""#include <{plugin_name}/init.h>
#include <sofa/core/ObjectFactory.h>

namespace {plugin_name}
{{

void initializePlugin() {{
    static bool first = true;
    if (first) {{
        first = false;
        // Register components here
    }}
}}


}}

extern "C" {{
    {upper_plugin_name}_API void initExternalModule() {{
        {plugin_name}::initializePlugin();
    }}

    {upper_plugin_name}_API const char* getModuleName() {{
        return {plugin_name}::MODULE_NAME;
    }}

    {upper_plugin_name}_API const char* getModuleVersion() {{
        return {plugin_name}::MODULE_VERSION;
    }}

    {upper_plugin_name}_API const char* getModuleLicense() {{
        return "LGPL";
    }}

    {upper_plugin_name}_API const char* getModuleDescription() {{
        return "SOFA plugin for {plugin_name}";
    }}
}}
"""
    create_file(os.path.join(plugin_src_path, "init.cpp"), init_cpp_content)

    # Create config.h.in
    config_h_content = f"""#pragma once
#include <sofa/config.h>

#ifdef SOFA_BUILD_{upper_plugin_name}
#  define SOFA_TARGET @PROJECT_NAME@
#  define {upper_plugin_name}_API SOFA_EXPORT_DYNAMIC_LIBRARY
#else
#  define {upper_plugin_name}_API SOFA_IMPORT_DYNAMIC_LIBRARY
#endif

namespace {plugin_name}
{{
    constexpr const char* MODULE_NAME = "@PROJECT_NAME@";
    constexpr const char* MODULE_VERSION = "@PROJECT_VERSION@";
}}
"""
    create_file(os.path.join(plugin_src_path, "config.h.in"), config_h_content)

    # Create tests folder and plugin subfolder
    tests_path = os.path.join(plugin_path, "tests")
    os.makedirs(tests_path)
    print(f"Created folder: {tests_path}")

    tests_cmake_content = f"""cmake_minimum_required(VERSION 3.12)
project({plugin_name}_test VERSION 1.0)
find_package(Sofa.Testing REQUIRED)

set(SOURCE_FILES
    test.cpp
)

add_executable(${{PROJECT_NAME}} ${{SOURCE_FILES}})

target_link_libraries(${{PROJECT_NAME}} Sofa.Testing {plugin_name})

add_test(NAME ${{PROJECT_NAME}} COMMAND ${{PROJECT_NAME}})
"""
    create_file(os.path.join(tests_path, "CMakeLists.txt"), tests_cmake_content)

    test_file_content = f"""#include <gtest/gtest.h>
"""
    create_file(os.path.join(tests_path, "test.cpp"), test_file_content)

if __name__ == "__main__":
    main()
