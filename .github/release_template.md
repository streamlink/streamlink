{{ changelog }}

## ⚙️ Installation and configuration

Please see the detailed [installation instructions](https://streamlink.github.io/install.html) and [CLI guide](https://streamlink.github.io/cli.html) on Streamlink's website.

**⚠️ PLEASE NOTE ⚠️**  
Streamlink's Windows installers have been moved to [streamlink/windows-installer](https://github.com/streamlink/windows-installer/releases).

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
