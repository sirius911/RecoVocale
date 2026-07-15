import win32clipboard as cb
import win32con


def _make_html_clip(text: str) -> bytes:
    import html
    # 1) Normalise et enlève un éventuel \n final
    esc = html.escape(text).replace("\r\n", "\n").replace("\r", "\n")
    esc = esc.rstrip("\n")
    # 2) Convertit les sauts de ligne restants en <br>
    esc = esc.replace("\n", "<br>\n")
    # 3) Utilise un élément inline pour éviter le retour à la ligne après collage
    html_body = f"<!--StartFragment--><span style='white-space:pre-wrap'>{esc}</span><!--EndFragment-->"
    full_html = f"<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>{html_body}</body></html>"

    header = (
        "Version:0.9\r\n"
        "StartHTML:{st_html:010d}\r\n"
        "EndHTML:{end_html:010d}\r\n"
        "StartFragment:{st_frag:010d}\r\n"
        "EndFragment:{end_frag:010d}\r\n"
    )
    temp_header = header.format(st_html=0, end_html=0, st_frag=0, end_frag=0)
    enc = "utf-8"
    start_html = len(temp_header.encode(enc))
    start_fragment = start_html + full_html.index("<!--StartFragment-->")
    end_fragment = start_html + full_html.index("<!--EndFragment-->") + len("<!--EndFragment-->")
    end_html = start_html + len(full_html.encode(enc))
    final_header = header.format(st_html=start_html, end_html=end_html, st_frag=start_fragment, end_frag=end_fragment)
    return (final_header + full_html).encode(enc)


def set_clipboard(text: str, html: bool = True, hwnd=None):
    # Sécurité : garantit toujours une chaîne
    text = str(text)

    # Normalise CRLF pour CF_UNICODETEXT
    text_win = text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')

    cb.OpenClipboard(hwnd)
    try:
        cb.EmptyClipboard()
        # 1) Texte Unicode standard
        cb.SetClipboardText(
            text_win,
            win32con.CF_UNICODETEXT
        )

        # 2) HTML Format (optionnel)
        if html:
            html_bytes = _make_html_clip(text)  # bytes
            fmt = cb.RegisterClipboardFormat("HTML Format")
            cb.SetClipboardData(fmt, html_bytes)
    finally:
        cb.CloseClipboard()


if __name__ == "__main__":
    text = "Test depuis pywin32\n — accents éèà ✓"
    set_clipboard(text, True)
    print(f"'{text}' -> clipboard windows OK")
