export interface ReportCitationPart {
  text: string
  citationKey: string | null
}

export function splitReportCitations(content: string): ReportCitationPart[] {
  // 中文注释：只识别后端 RAG 生成的 [E1] 形态，避免误伤普通 Markdown。
  const matches = content.matchAll(/\[(E\d+)\]/g)
  const parts: ReportCitationPart[] = []
  let lastIndex = 0
  for (const match of matches) {
    const start = match.index ?? 0
    if (start > lastIndex) {
      parts.push({ text: content.slice(lastIndex, start), citationKey: null })
    }
    parts.push({ text: match[0], citationKey: match[1] })
    lastIndex = start + match[0].length
  }
  if (lastIndex < content.length) {
    parts.push({ text: content.slice(lastIndex), citationKey: null })
  }
  return parts.length ? parts : [{ text: content, citationKey: null }]
}
