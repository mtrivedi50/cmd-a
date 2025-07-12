declare module "@fontsource/*" {}
declare module "react-syntax-highlighter";
declare module "react-syntax-highlighter/*";
declare module "*.svg?react" {
  import * as React from "react";
  const ReactComponent: React.FC<React.SVGProps<SVGSVGElement>>;
  export default ReactComponent;
}
