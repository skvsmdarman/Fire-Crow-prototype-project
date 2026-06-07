import { useState, useEffect } from "react";
import { getPolicyContext } from "./api";
import { PRIVACY_POLICY_VERSION, TERMS_VERSION } from "../../lib/policy";

export function usePolicyContext() {
  const [activePrivacyVersion, setActivePrivacyVersion] = useState(PRIVACY_POLICY_VERSION);
  const [activeTermsVersion, setActiveTermsVersion] = useState(TERMS_VERSION);
  const [loadingContext, setLoadingContext] = useState(true);
  const [providerAvailability, setProviderAvailability] = useState({
    github: false,
    google: false,
    password: false,
  });

  useEffect(() => {
    let active = true;

    async function loadPolicyContext() {
      try {
        const data = await getPolicyContext();
        if (active) {
          setActivePrivacyVersion(data.privacy_policy_version || PRIVACY_POLICY_VERSION);
          setActiveTermsVersion(data.terms_version || TERMS_VERSION);
          setProviderAvailability(data.providers);
        }
      } catch (err) {
        console.warn("Using default policy fallback versions:", err);
      } finally {
        if (active) setLoadingContext(false);
      }
    }

    loadPolicyContext();
    return () => {
      active = false;
    };
  }, []);

  return {
    activePrivacyVersion,
    activeTermsVersion,
    loadingContext,
    providerAvailability,
  };
}
