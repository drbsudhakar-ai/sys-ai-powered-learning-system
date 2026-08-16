export default function RegistrationDisabledPage() {
  return null;
}

export function getServerSideProps() {
  return {
    redirect: {
      destination: "/login?reason=registration-disabled",
      permanent: false,
    },
  };
}

RegistrationDisabledPage.getLayout = (page) => page;
