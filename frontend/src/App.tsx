import "@/App.css";
import "@fontsource/inter";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/inter/700.css";
import { Routes, Route } from "react-router-dom";

import SignIn from "@components/login/SignIn";
import SignUp from "@components/login/SignUp";
import PrivateRoute from "@components/PrivateRoute";
import AddIntegrations from "@components/integrations/add_integrations/AddIntegrations";
import ListIntegrations from "@components/integrations/list_integrations/ListIntegrations";
import SlackIntegrationForm from "@/components/integrations/forms/SlackIntegrationForm";
import GithubIntegrationForm from "@/components/integrations/forms/GithubIntegrationForm";
import { ThemeProvider } from "@mui/material";
import theme from "@/theme/theme";
import { Secrets } from "@/components/secrets/Secrets";
import { ChatModels } from "@/components/chat_models/ChatModels";
import Home from "@/components/chat/Home";
import { ChatProvider } from "@/contexts/ChatContext";
import ChatInterface from "@/components/chat/ChatInterface";
import ChatEntrypoint from "@/components/chat/ChatEntrypoint";
import { IntegrationProvider } from "@/contexts/IntegrationContext";
import { ChatModelProvider } from "@/contexts/ChatModelContext";
import { SecretProvider } from "@/contexts/SecretContext";

function App() {
  return (
    <>
      <ThemeProvider theme={theme}>
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<SignIn />} />
          <Route path="/signup" element={<SignUp />} />
          {/* Private routes */}
          <Route
            path="/*"
            element={
              <IntegrationProvider>
                <ChatModelProvider>
                  <SecretProvider>
                    <Routes>
                      {/* Private routes with the navbar */}
                      <Route
                        path="/dashboard"
                        element={<PrivateRoute showNavbar={true} />}
                      >
                        <Route
                          path=""
                          element={
                            <ChatProvider>
                              <Home>
                                <ChatEntrypoint />
                              </Home>
                            </ChatProvider>
                          }
                        />
                      </Route>
                      <Route
                        path="/dashboard/c/:id"
                        element={<PrivateRoute showNavbar={true} />}
                      >
                        <Route
                          path=""
                          element={
                            <ChatProvider>
                              <Home>
                                <ChatInterface />
                              </Home>
                            </ChatProvider>
                          }
                        />
                      </Route>
                      <Route
                        path="/integrations"
                        element={<PrivateRoute showNavbar={true} />}
                      >
                        <Route path="" element={<ListIntegrations />} />
                        <Route path="add" element={<AddIntegrations />} />
                        <Route
                          path="add/slack"
                          element={<SlackIntegrationForm />}
                        />
                        <Route
                          path="add/github"
                          element={<GithubIntegrationForm />}
                        />
                      </Route>
                      <Route
                        path="/chat_models"
                        element={<PrivateRoute showNavbar={true} />}
                      >
                        <Route path="" element={<ChatModels />} />
                      </Route>
                      <Route
                        path="/api_keys"
                        element={<PrivateRoute showNavbar={true} />}
                      >
                        <Route path="" element={<Secrets />} />
                      </Route>
                    </Routes>
                  </SecretProvider>
                </ChatModelProvider>
              </IntegrationProvider>
            }
          />
        </Routes>
      </ThemeProvider>
    </>
  );
}

export default App;
