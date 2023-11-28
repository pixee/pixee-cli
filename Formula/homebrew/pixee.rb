class Pixee < Formula
  include Language::Python::Virtualenv

  desc "Fix and prevent bugs and security vulnerabilities in your code"
  homepage "https://pixee.ai"
  url "https://github.com/pixee/pixee-cli.git"
  version "0.1.0"

  depends_on "python@3.11"
  depends_on "openjdk@17"

end
