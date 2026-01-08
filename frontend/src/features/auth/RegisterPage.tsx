import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useNavigate } from "react-router-dom";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { registerSchema, type RegisterValues } from "./schema";
import { useRegister } from "./useAuthMutations";

/**
 * Register screen (AUTH-01, D-09/D-10/D-12).
 *
 * RHF + zodResolver inline validation with the exact UI-SPEC messages. On a 409
 * a form-level destructive message offers a link to log in instead. On success
 * the user is auto-logged-in (token stored in useRegister, D-10) and navigated
 * to the protected app root. Cross-links to /login (D-09).
 */
export default function RegisterPage() {
  const navigate = useNavigate();
  const register = useRegister();

  const form = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = (values: RegisterValues) => {
    register.mutate(values, {
      onSuccess: () => navigate("/", { replace: true }),
    });
  };

  const emailExists = register.isError && register.error.status === 409;

  return (
    <div className="flex min-h-svh items-center justify-center bg-muted p-8">
      <div className="w-full max-w-sm rounded-lg border bg-background p-6 shadow-sm">
        <h1 className="text-2xl font-semibold leading-tight tracking-tight">
          Create your account
        </h1>

        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            className="mt-6 grid gap-4"
            noValidate
          >
            {register.isError && (
              <p role="alert" className="text-sm font-medium text-destructive">
                {emailExists ? (
                  <>
                    An account with this email already exists.{" "}
                    <Link to="/login" className="underline">
                      Log in
                    </Link>{" "}
                    instead.
                  </>
                ) : (
                  register.error.message
                )}
              </p>
            )}

            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Email</FormLabel>
                  <FormControl>
                    <Input
                      type="email"
                      autoComplete="email"
                      placeholder="you@example.com"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Password</FormLabel>
                  <FormControl>
                    <Input
                      type="password"
                      autoComplete="new-password"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <Button
              type="submit"
              className="w-full"
              disabled={register.isPending}
            >
              {register.isPending ? "Creating account…" : "Create account"}
            </Button>
          </form>
        </Form>

        <p className="mt-4 text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-foreground underline">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
