{{ changelog }}

## 📦 Download and Installation

Please see the [installation instructions](https://streamlink.github.io/install.html) for a list of available install methods and packages on the supported operating systems.

**⚠️ PLEASE NOTE ⚠️**  
Streamlink's Windows installers have been moved to [streamlink/windows-builds](https://github.com/streamlink/windows-builds).

## ⚙️ Configuration and Usage

Please see the [CLI documentation](https://streamlink.github.io/cli.html) for how to configure and use Streamlink.

## ❤️ Support

If you think that Streamlink is useful and if you want to keep the project alive, then please consider supporting its maintainers by sending a small and optionally recurring tip via the [available options](https://streamlink.github.io/donate.html).  
Your support is very much appreciated, thank you!
{%- if contributors %}

## 🙏 Contributors
{% for contributor in contributors %}
- {{ contributor.commits }}: @{{ contributor.name }}
{%- endfor %}
{%- endif %}
{%- if gitshortlog %}

## 🗒️ Full changelog

```text
{{ gitshortlog }}
```
{%- endif %}
