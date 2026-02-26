// We cannot import types in this environment for some reason when using node --experimental-strip-types
// It seems it strips types but might have issues with type-only imports or maybe I am misinterpreting the error.
// "SyntaxError: The requested module './types.ts' does not provide an export named 'TransactionStatus'"
// This usually happens when the file is treated as a module but the export is a type and it gets stripped out but the import remains?
// Or maybe because it's a type-only file?

// Let's just use string for the input type in this utility file to avoid the import issue during testing.
// In the actual component we can use the type.

export const getTransactionStatus = (status: string) => {
    switch (status) {
        case 'pending':
        case 'sent_to_kafka':
            return 'pending';
        case 'cleared':
            return 'cleared';
        default:
            return 'unknown';
    }
};

export const getStatusLabel = (status: string) => {
    switch (status) {
        case 'pending':
            return 'Pending';
        case 'cleared':
            return 'Cleared';
        default:
            return 'Unknown Status';
    }
};
