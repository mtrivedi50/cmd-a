import Box from "@mui/material/Box";
import Link from "@mui/material/Link";

import { toProperCase } from "@components/login/utils";

export default function NavLink({ paths }: { paths: string[] }) {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "row",
        pt: 1,
        pb: 1,
        alignItems: "center",
      }}
    >
      {paths.map((link, idx) => {
        return (
          <>
            <Link
              key={idx}
              href={"/" + paths.slice(0, idx + 1).join("/")}
              sx={{
                fontSize: "0.8rem",
                mr: idx === paths.length - 1 ? 0 : 1,
                ml: idx === 0 ? 0 : 1,
              }}
            >
              {toProperCase(link)}
            </Link>
            {idx < paths.length - 1 && " / "}
          </>
        );
      })}
    </Box>
  );
}
