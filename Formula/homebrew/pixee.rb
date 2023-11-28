class Pixee < Formula
  include Language::Python::Virtualenv

  desc "Fix and prevent bugs and security vulnerabilities in your code"
  homepage "https://pixee.ai"
  url "https://github.com/pixee/pixee-cli.git"
  head "https://github.com/pixee/pixee-cli.git", branch: "main"
  license "MIT"
  version "0.1.0"

  depends_on "python@3.11"
  depends_on "openjdk@17"

  resource "codemodder" do
    url "https://files.pythonhosted.org/packages/18/ae/ce5f2d1d6f632f728e173be52212fe29d601a3a3146c35cb725217d7190f/codemodder-0.64.5.tar.gz"
    sha256 "752f0fc447b26bd1b913ed6df508bc8b7b21ec1159086c0107eecc48e9b1c55e"
  end

end
