# install_all_languages.py (Corrected Version)
import argostranslate.package
import argostranslate.translate
import time

def install_all():
    print("Updating package index...")
    argostranslate.package.update_package_index()

    available_packages = argostranslate.package.get_available_packages()
    installed_languages = {lang.code for lang in argostranslate.translate.load_installed_languages()}

    print(f"Found {len(available_packages)} available packages.")

    for i, package in enumerate(available_packages):
        # Check if the languages in the package are already installed to avoid redundant downloads
        # NOTE: We still use .from_code and .to_code here, which is correct
        if package.from_code in installed_languages and package.to_code in installed_languages:
            # This is the corrected line:
            print(f"[{i+1}/{len(available_packages)}] Skipping {package.from_name} -> {package.to_name} (already installed)")
            continue

        # And this is the other corrected line:
        print(f"[{i+1}/{len(available_packages)}] Downloading and installing: {package.from_name} -> {package.to_name}...")
        try:
            package.install()
            # Update our set of installed languages
            installed_languages.add(package.from_code)
            installed_languages.add(package.to_code)
            time.sleep(1) # Small delay to be polite to the server
        except Exception as e:
            print(f"    --> Could not install package {package}. Error: {e}")

    print("\nInstallation of all available language models is complete!")

if __name__ == "__main__":
    install_all()