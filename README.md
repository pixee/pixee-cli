<picture>
  <source media="(prefers-color-scheme: dark)" srcset="img/dark_mode_logo.png">
  <source media="(prefers-color-scheme: light)" srcset="img/light_mode_logo.png">
  <img alt="Pixee Logo" src="https://github.com/pixee/pixee-cli/raw/main/img/light_mode_logo.png">
</picture>

# Pixee is your automated product security engineer

*Pixee fixes vulnerabilities, hardens code, squashes bugs, and gives
engineers more time to focus on the work that counts.*

The Pixee CLI brings the power of Pixee's [Codemodder framework](https://codemodder.io) to your local development environment. This provides a way for developers to try out Pixee before installing the GitHub app.

![Pixee CLI Demo](https://github.com/pixee/pixee-cli/raw/main/img/demo.gif)
Learn more at https://pixee.ai! 

Get the most out of Pixee by installing the Pixeebot GitHub app at
https://app.pixee.ai. Or find us on [GitHub Marketplace](https://github.com/apps/pixeebot). 

## Supported Systems:
* MacOS (using [homebrew](https://brew.sh))
* Linux (coming soon!)

## Installation

### MacOS (using homebrew)

```
brew tap pixee/pixee
brew install pixee
```

## Usage

After installation, run the `pixee` command to see instructions and options.

## F.A.Q.

### What languages are supported for fixes?
Currently we support codemods for Java and Python. Stay tuned for additional language support at https://pixee.ai!

### What happens to my code?
The Pixee CLI currently runs most detection and fixes locally to your own host machine. Any features that require network access to a third-party service (e.g. OpenAI) will require explicit opt-in. We promise to be transparent when this is the case.

### How can I install the GitHub application?
Get the most out of Pixee by installing the Pixeebot GitHub app at https://app.pixee.ai. Or find us on [GitHub Marketplace](https://github.com/apps/pixeebot).

### Where can I request features and report issues?
For CLI feature requests and bug reports please use our GitHub issue tracker: https://github.com/pixee/pixee-cli/issues


## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md).
