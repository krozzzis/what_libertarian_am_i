# SPDX-License-Identifier: Unlicense
{
  inputs = {
    # nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    # systems.url = "github:nix-systems/default";
  };

  outputs =
    { nixpkgs, ... }:
    let
      eachSystem =
        f:
        nixpkgs.lib.genAttrs nixpkgs.lib.systems.flakeExposed (system: f nixpkgs.legacyPackages.${system});
    in
    {
      devShells = eachSystem (pkgs: {
        default = pkgs.mkShell {
          buildInputs = [
            pkgs.python3
            pkgs.uv
            pkgs.basedpyright
            pkgs.stdenv.cc.cc.lib
          ];
          shellHook = ''
            export LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath [ pkgs.stdenv.cc.cc.lib ]}:$LD_LIBRARY_PATH
          '';
        };
      });
    };
}
