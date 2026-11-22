Found a 11 line (51 tokens) duplication in the following files:
* Starting at line 86 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\core.py
* Starting at line 104 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\core.py

```python
    except KeyboardInterrupt:
        env.stderr.write('\n')
        if include_traceback:
            raise
        exit_status = ExitStatus.ERROR_CTRL_C
    except SystemExit as e:
        if e.code != ExitStatus.SUCCESS:
            env.stderr.write('\n')
            if include_traceback:
                raise
            exit_status = ExitStatus.ERROR
```

---

Found a 5 line (44 tokens) duplication in the following files:
* Starting at line 59 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\cli\argparser.py
* Starting at line 580 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\cli\argparser.py

```python
        _, exception, _ = sys.exc_info()
        if (
            isinstance(exception, argparse.ArgumentError)
            and len(exception.args) >= 1
            and isinstance(exception.args[0], argparse.Action)
```

---

Found a 6 line (33 tokens) duplication in the following files:
* Starting at line 97 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\cli\argparser.py
* Starting at line 159 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\cli\argparser.py

```python
        self.args, no_options = self.parse_known_args(args, namespace)
        if self.args.debug:
            self.args.traceback = True
        self.has_stdin_data = (
            self.env.stdin
            and not getattr(self.args, 'ignore_stdin', False)
```

---

Found a 5 line (33 tokens) duplication in the following files:
* Starting at line 39 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\output\lexers\metadata.py
* Starting at line 50 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\output\lexers\metadata.py

```python
                fr'({ELAPSED_TIME_LABEL})( *)(:)( *)(\d+\.\d+)(s)', pygments.lexer.bygroups(
                    pygments.token.Name.Decorator,  # Name
                    pygments.token.Text,
                    pygments.token.Operator,  # Colon
                    pygments.token.Text,
```

---

Found a 4 line (31 tokens) duplication in the following files:
* Starting at line 146 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\core.py
* Starting at line 32 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\manager\__main__.py

```python
def main(
    args: List[Union[str, bytes]] = sys.argv,
    env: Environment = Environment()
) -> ExitStatus:
```

---

Found a 8 line (30 tokens) duplication in the following files:
* Starting at line 90 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\cli\argparser.py
* Starting at line 151 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\cli\argparser.py

```python
    def parse_args(
        self,
        env: Environment,
        args=None,
        namespace=None
    ) -> argparse.Namespace:
        self.env = env
        self.args, no_options = self.parse_known_args(args, namespace)
```

---

Found a 5 line (30 tokens) duplication in the following files:
* Starting at line 4 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\output\formatters\headers.py
* Starting at line 6 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\output\formatters\json.py
* Starting at line 53 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\output\formatters\xml.py

```python
class HeadersFormatter(FormatterPlugin):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.enabled = self.format_options['headers']['sort']
```

---

Found a 4 line (30 tokens) duplication in the following files:
* Starting at line 62 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\output\ui\rich_progress.py
* Starting at line 97 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\output\ui\rich_progress.py

```python
class StatusDisplay(BaseDisplay):
    def start(
        self, *, total: Optional[float], at: float, description: str
    ) -> None:
```

---

Found a 8 line (28 tokens) duplication in the following files:
* Starting at line 431 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\cli\argparser.py
* Starting at line 459 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\cli\argparser.py

```python
            except argparse.ArgumentTypeError as e:
                if self.args.traceback:
                    raise
                self.error(e.args[0])

            else:
                # Set the URL correctly
                self.args.url = self.args.method
```

---

Found a 3 line (26 tokens) duplication in the following files:
* Starting at line 14 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\output\ui\rich_progress.py
* Starting at line 63 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\output\ui\rich_progress.py
* Starting at line 98 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\output\ui\rich_progress.py

```python
    def start(
        self, *, total: Optional[float], at: float, description: str
    ) -> None:
```

---

Found a 3 line (25 tokens) duplication in the following files:
* Starting at line 97 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\config.py
* Starting at line 183 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\sessions.py

```python
        return data

    def post_process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
```

---

Found a 4 line (25 tokens) duplication in the following files:
* Starting at line 149 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\uploads.py
* Starting at line 195 of C:\Users\itste\IdeaProjects\SOEN-6431-Group-Project\httpie\uploads.py

```python
    callback: CallbackT,
    chunked: bool = False,
    content_length_header_value: Optional[int] = None,
) -> Union[bytes, IO, ChunkedStream]:
```
