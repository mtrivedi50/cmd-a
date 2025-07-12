import Markdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import supersub from "remark-supersub";

export function MarkdownRenderer({ children }: { children: string }) {
  return (
    <Markdown
      remarkPlugins={[supersub]}
      components={{
        // eslint-disable-next-line  @typescript-eslint/no-explicit-any
        code(props): any {
          // From react-markdown documentation
          // https://github.com/remarkjs/react-markdown?tab=readme-ov-file#components
          const { children, className, ...rest } = props;
          const match = /language-(\w+)/.exec(className || "");
          return match ? (
            <SyntaxHighlighter
              {...rest}
              PreTag="div"
              children={String(children).replace(/\n$/, "")}
              language={match[1]}
              customStyle={{
                fontSize: "0.95rem",
                borderRadius: "10px",
              }}
              style={vscDarkPlus}
            />
          ) : (
            <code {...rest} className={"inline-code"}>
              {children}
            </code>
          );
        },
      }}
    >
      {children}
    </Markdown>
  );
}
