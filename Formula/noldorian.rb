# Homebrew formula — the noldorian repo doubles as a tap (no separate
# homebrew-* repo needed):
#
#   brew tap everplay-tech/noldorian https://github.com/Everplay-Tech/noldorian.git
#   brew install everplay-tech/noldorian/noldorian
#
# NOTE: formula for CLIs (keyabra/xalakazam/xadabra/abra/xabra) — there is no
# cask; casks are for GUI app bundles and these are terminal tools.
# STATUS: scaffold, authored 2026-07-08 — not yet exercised by a real
# `brew install` (pip/bootstrap is the proven path; this exists for
# brew-native macOS setups).
class Noldorian < Formula
  desc "Everplay-Tech operator CLIs: keyabra, xalakazam, xadabra, abra, xabra"
  homepage "https://github.com/Everplay-Tech/noldorian"
  url "https://github.com/Everplay-Tech/noldorian.git", branch: "main"
  version "0.2.0"
  license "Apache-2.0"

  depends_on "python@3.12"

  def install
    venv = libexec/"venv"
    system Formula["python@3.12"].opt_bin/"python3.12", "-m", "venv", venv
    %w[keyabra xalakazam xadabra binabra xabra].each do |pkg|
      system venv/"bin/pip", "install", "--quiet", buildpath/pkg
    end
    %w[keyabra xalakazam xadabra abra xabra].each do |cli|
      bin.install_symlink venv/"bin"/cli
    end
  end

  test do
    assert_match "keyabra", shell_output("#{bin}/keyabra --version")
    assert_match "xalakazam", shell_output("#{bin}/xalakazam --version")
  end
end
