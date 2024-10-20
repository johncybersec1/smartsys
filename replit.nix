{pkgs}: {
  deps = [
    pkgs.glibcLocales
    pkgs.rustc
    pkgs.openssl
    pkgs.libxcrypt
    pkgs.libiconv
    pkgs.cargo
    pkgs.pkg-config
  ];
}
