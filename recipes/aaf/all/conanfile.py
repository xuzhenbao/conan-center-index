from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name, is_apple_os
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
import os

required_conan_version = ">=1.52.0"


class AafConan(ConanFile):
    name = "aaf"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://sourceforge.net/projects/aaf/"
    description = (
        "A cross-platform SDK for AAF. AAF is a metadata management system and "
        "file format for use in professional multimedia creation and authoring."
    )
    topics = ("multimedia", "crossplatform")
    license = "AAFSDKPSL-2.0"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "structured_storage": [True, False],
    }
    default_options = {
        "structured_storage": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("expat/2.5.0")
        self.requires("libjpeg/9e")
        if self.settings.os in ("FreeBSD", "Linux"):
            self.requires("libuuid/1.0.3")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if is_apple_os(self):
            tc.cache_variables["PLATFORM"] = "apple-clang"
        elif self.settings.compiler == "Visual Studio":
            tc.cache_variables["PLATFORM"] = "vc"
        else:
            tc.cache_variables["PLATFORM"] = str(self.settings.os)
        # ARCH is used only for setting the output directory, except if host is macOS
        # where ARCH is used to select proper pre-compiled proprietary Structured Storage library.
        if self.settings.os == "Macos" and self.settings.arch == "armv8":
            tc.cache_variables["ARCH"] = "arm64"
        else:
            tc.cache_variables["ARCH"] = "x86_64"
        tc.cache_variables["AAF_NO_STRUCTURED_STORAGE"] = not self.options.structured_storage
        jpeg_res_dirs = ";".join([p.replace("\\", "/") for p in self.dependencies["libjpeg"].cpp_info.aggregated_components().resdirs])
        tc.variables["JPEG_RES_DIRS"] = jpeg_res_dirs
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "AAFSDKPSL.TXT", src=os.path.join(self.source_folder, "LEGAL"), dst=os.path.join(self.package_folder, "licenses"))
        out_include_folder = os.path.join(self.source_folder, "out", "shared", "include")
        out_target_folder = os.path.join(self.source_folder, "out", "target")
        copy(self, "*.h", src=out_include_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "*/RefImpl/*.dll", src=out_target_folder, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "*/RefImpl/*.lib", src=out_target_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*/RefImpl/*.so*", src=out_target_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*/RefImpl/*.dylib", src=out_target_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*/RefImpl/*.a", src=out_target_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        fix_apple_shared_install_name(self)

    def package_info(self):
        if self.settings.os == "Windows":
            suffix = "D" if self.settings.build_type == "Debug" else ""
            self.cpp_info.libs = [f"AAF{suffix}", f"AAFIID{suffix}", "AAFCOAPI"]
        else:
            self.cpp_info.libs = ["aaflib", "aafiid", "com-api"]
        if self.settings.os in ("FreeBSD", "Linux"):
            self.cpp_info.system_libs = ["dl"]
        elif is_apple_os(self):
            self.cpp_info.frameworks = ["CoreServices", "CoreFoundation"]
