// Standalone L^ core reproducer. No LOVE, assets, graphics, or worker threads.
// Reusing a single live value must not make a weak cache grow with history.
#include <stdio.h>
#include "lhat/vm.h"
#include "machine.h"

static unsigned char keys[100000];

int main(void)
{
    LhatMachine *machine = lhat_machine_new();
    if (!machine) return 1;
    Machine *m = (Machine *)machine;
    for (size_t i = 0; i < sizeof keys; ++i) {
        if (!lhat_machine_weak_cache_put(machine, &keys[i], lhat_integer(42))) return 2;
        if (lhat_is_nil(lhat_machine_weak_cache_get(machine, &keys[i]))) return 3;
        lhat_machine_weak_cache_forget(machine, &keys[i]);
        if ((i + 1) % 10000 == 0)
            printf("operations=%zu live=%zu capacity=%zu bytes=%zu\n",
                   i + 1, m->weak_count, m->weak_capacity,
                   m->weak_capacity * sizeof(LhatWeakEntry));
    }
    int failed = m->weak_count != 0 || m->weak_capacity > 16;
    lhat_machine_dispose(machine);
    return failed;
}
