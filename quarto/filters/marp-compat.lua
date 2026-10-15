-- Marp parity for Quarto revealjs (slide-level 0, commonmark_x reader).

-- Quarto appends `::: {.quarto-auto-generated-content style='display: none;'}`
-- to every document; commonmark_x rejects single-quoted attribute values, so
-- the fence arrives as two literal paragraphs around the content. Rebuild the
-- Div so it does not leak onto the last slide.
local function fence_open(b)
  if b.t ~= "Para" then return nil end
  local s = pandoc.utils.stringify(b)
  return s:match("^:::+%s*{%.([%w%-]+)")
end

local function fence_close(b)
  return b.t == "Para" and pandoc.utils.stringify(b):match("^:::+%s*$") ~= nil
end

function Blocks(blocks)
  local out, i = pandoc.Blocks{}, 1
  while i <= #blocks do
    local cls = fence_open(blocks[i])
    local j = i + 1
    if cls then
      while j <= #blocks and not fence_close(blocks[j]) do j = j + 1 end
    end
    if cls and j <= #blocks then
      local inner = pandoc.Blocks{}
      for k = i + 1, j - 1 do inner:insert(blocks[k]) end
      out:insert(pandoc.Div(inner, pandoc.Attr("", {cls}, {style = "display: none;"})))
      i = j + 1
    else
      out:insert(blocks[i])
      i = i + 1
    end
  end
  return out
end

-- Pandoc turns a Div whose first block is a heading into a <section>
-- (section-divs), and reveal.js then treats that nested <section> as a
-- vertical slide. Keep it a plain <div>, as under Marp: lead it with an empty
-- raw block so the heading is no longer first. (Raw `<div>` HTML is untouched
-- under commonmark_x; this covers Quarto-native `::: {.x}` divs.)
function Div(el)
  if el.content[1] and el.content[1].t == "Header" then
    el.content:insert(1, pandoc.RawBlock("html", "<!---->"))
    return el
  end
end

-- A deck's own <style> blocks get the same treatment as the themes
-- (scripts/port_theme.py): Marpit scopes them to the slide and makes `rem`
-- slide-relative, so `section.small { font-size: .8em }` must keep working.
local PORT = pandoc.path.join({pandoc.path.directory(PANDOC_SCRIPT_FILE), "..", "scripts", "port_theme.py"})

local function port_styles(html)
  if not html:find("<style", 1, true) then return nil end
  local changed = false
  local out = html:gsub("(<style[^>]*>)(.-)(</style>)", function(open, css, close)
    if open:find("scoped", 1, true) then return nil end
    changed = true
    return open .. pandoc.pipe("python3", {PORT, "-"}, css) .. close
  end)
  return changed and out or nil
end

function RawBlock(el)
  if el.format == "html" then
    local out = port_styles(el.text)
    if out then el.text = out; return el end
  end
end

return {{Blocks = Blocks}, {Div = Div, RawBlock = RawBlock}}
