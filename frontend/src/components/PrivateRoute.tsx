import { Navigate, Outlet, useLocation } from "react-router-dom";
import { Navbar } from "@/components/navbar/Navbar";
import { Box } from "@mui/material";
import { appBarHeight } from "@/theme/theme";

export default function PrivateRoute({ showNavbar }: { showNavbar: boolean }) {
  const isLoggedIn = !!localStorage.getItem("authToken");
  const location = useLocation();
  if (!isLoggedIn) {
    return <Navigate to="/" state={{ from: location }} replace />;
  }
  return (
    <>
      {showNavbar && (
        <>
          <Navbar />
          <Box sx={{ marginTop: appBarHeight }}>
            <Outlet />
          </Box>
        </>
      )}{" "}
    </>
  );
}
